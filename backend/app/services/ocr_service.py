"""
Production OCR and Expiry-Date Extraction Engine for Packaged Dairy Products.
Uses RapidOCR (ONNX Runtime, CPU-optimized) with OpenCV multi-stage preprocessing,
horizontal token line merging, regex semantic pattern matching, date normalization,
and date status computation.

Handles:
- Manufacturing dates (MFG, PKD) vs Expiry dates (EXP, USE BY, BEST BEFORE)
- Date formats: DD/MM/YYYY, DD-MM-YY, DD.MM.YYYY, YYYY-MM-DD, DD MMM YYYY, MMM YYYY
- Dot-matrix printed dates on milk cartons, pouches, paneer packets, and yogurt tubs
- Expiry status: Expired, Expiring Soon, Fresh, Uncertain
- Zero mock / fake fallback
"""

import os
import re
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple, Dict, Any, List
import cv2
import numpy as np

logger = logging.getLogger(__name__)

DAIRY_SHELF_LIFE_DAYS = {
    "packaged_milk": 5,
    "milk": 5,
    "packaged_paneer": 7,
    "paneer": 7,
    "packaged_yogurt": 10,
    "yogurt": 10,
    "curd": 7,
    "dahi": 7,
    "butter": 30,
    "cheese": 14
}

MONTH_MAP = {
    "JAN": 1, "JANUARY": 1,
    "FEB": 2, "FEBRUARY": 2,
    "MAR": 3, "MARCH": 3,
    "APR": 4, "APRIL": 4,
    "MAY": 5,
    "JUN": 6, "JUNE": 6,
    "JUL": 7, "JULY": 7,
    "AUG": 8, "AUGUST": 8,
    "SEP": 9, "SEPT": 9, "SEPTEMBER": 9,
    "OCT": 10, "OCTOBER": 10,
    "NOV": 11, "NOVEMBER": 11,
    "DEC": 12, "DECEMBER": 12
}

# 3-part complete date regexes (highest priority)
FULL_DATE_REGEXES = [
    # DD/MM/YYYY, DD-MM-YYYY, DD.MM.YYYY
    r'(?P<day>0?[1-9]|[12][0-9]|3[01])[\/\-\.\s](?P<month>0?[1-9]|1[0-2])[\/\-\.\s](?P<year>20[2-3][0-9])\b',
    # DD/MM/YY, DD-MM-YY, DD.MM.YY
    r'(?P<day>0?[1-9]|[12][0-9]|3[01])[\/\-\.\s](?P<month>0?[1-9]|1[0-2])[\/\-\.\s](?P<year>[2-3][0-9])\b',
    # YYYY-MM-DD, YYYY/MM/DD
    r'(?P<year>20[2-3][0-9])[\/\-\.](?P<month>0?[1-9]|1[0-2])[\/\-\.](?P<day>0?[1-9]|[12][0-9]|3[01])\b',
    # DD MMM YYYY / DD MMM YY (e.g., 25 NOV 2026, 06 JUN 24)
    r'(?P<day>0?[1-9]|[12][0-9]|3[01])[\s\-\/\.](?P<month_str>JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)[A-Z]*[\s\-\/\.](?P<year>(?:20)?[2-3][0-9])\b',
]

# 2-part month-year regexes (secondary fallback)
MONTH_YEAR_REGEXES = [
    # MMM YYYY (e.g. NOV 2026)
    r'\b(?P<month_str>JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)[A-Z]*[\s\-\/\.](?P<year>20[2-3][0-9])\b',
    # MM/YYYY (e.g. 11/2026)
    r'(?<!\d[\/\-\.\s])(?P<month>0?[1-9]|1[0-2])[\/\-\.](?P<year>20[2-3][0-9])\b',
]

class DairyExpiryOCREngine:
    def __init__(self):
        self._ocr = None

    @property
    def ocr(self):
        if self._ocr is None:
            try:
                import gc
                gc.collect()
                from rapidocr_onnxruntime import RapidOCR
                self._ocr = RapidOCR(det_limit_type='max', det_limit_side_len=960)
                logger.info("RapidOCR ONNX Runtime engine initialized.")
            except Exception as e:
                logger.warning(f"RapidOCR initial load exception: {e}. Retrying with gc.collect()...")
                try:
                    import gc
                    gc.collect()
                    from rapidocr_onnxruntime import RapidOCR
                    self._ocr = RapidOCR(det_limit_type='max', det_limit_side_len=960)
                    logger.info("RapidOCR initialized on retry.")
                except Exception as e2:
                    logger.error(f"Failed to initialize RapidOCR: {e2}")
                    self._ocr = None
        return self._ocr

    def _preprocess_variants(self, img_bgr: np.ndarray) -> List[np.ndarray]:
        variants = [img_bgr]
        h, w = img_bgr.shape[:2]

        # Grayscale + CLAHE
        gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
        clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
        cl = clahe.apply(gray)
        variants.append(cv2.cvtColor(cl, cv2.COLOR_GRAY2BGR))

        # Upscaled if low resolution
        if max(h, w) < 900:
            scale = 1000.0 / max(h, w)
            upscaled = cv2.resize(img_bgr, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_CUBIC)
            variants.append(upscaled)

        return variants

    def _assemble_lines(self, ocr_results: List[Any]) -> List[Tuple[str, float]]:
        """
        Groups horizontally adjacent word tokens on the same line into coherent text lines.
        """
        if not ocr_results:
            return []

        # Each item: [box, text, score]
        items = []
        for it in ocr_results:
            box, text, score = it[0], it[1].strip(), float(it[2])
            pts = np.array(box)
            ymin, ymax = pts[:, 1].min(), pts[:, 1].max()
            xmin, xmax = pts[:, 0].min(), pts[:, 0].max()
            ymid = (ymin + ymax) / 2.0
            height = max(1.0, ymax - ymin)
            items.append({
                "text": text,
                "score": score,
                "xmin": xmin,
                "xmax": xmax,
                "ymin": ymin,
                "ymax": ymax,
                "ymid": ymid,
                "height": height
            })

        # Sort items vertically
        items.sort(key=lambda it: it["ymid"])

        lines = []
        current_line = [items[0]]

        for it in items[1:]:
            prev_ymid = np.mean([x["ymid"] for x in current_line])
            avg_height = np.mean([x["height"] for x in current_line])
            # If vertical distance is small relative to font height, group in same line
            if abs(it["ymid"] - prev_ymid) < avg_height * 0.75:
                current_line.append(it)
            else:
                current_line.sort(key=lambda x: x["xmin"])
                line_text = " ".join([x["text"] for x in current_line])
                line_score = float(np.mean([x["score"] for x in current_line]))
                lines.append((line_text, line_score))
                current_line = [it]

        if current_line:
            current_line.sort(key=lambda x: x["xmin"])
            line_text = " ".join([x["text"] for x in current_line])
            line_score = float(np.mean([x["score"] for x in current_line]))
            lines.append((line_text, line_score))

        return lines

    def _parse_matched_date(self, match: re.Match) -> Optional[datetime]:
        gd = match.groupdict()
        try:
            raw_yr = gd.get("year", "")
            if len(raw_yr) == 2:
                year = 2000 + int(raw_yr)
            else:
                year = int(raw_yr)

            if "month_str" in gd and gd["month_str"]:
                month = MONTH_MAP.get(gd["month_str"].upper()[:3], 1)
            elif "month" in gd and gd["month"]:
                month = int(gd["month"])
            else:
                return None

            if "day" in gd and gd["day"]:
                day = int(gd["day"])
            else:
                # Month-only format: default to end of that month
                if month in [1, 3, 5, 7, 8, 10, 12]:
                    day = 31
                elif month in [4, 6, 9, 11]:
                    day = 30
                else:
                    day = 29 if (year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)) else 28

            if 1 <= month <= 12 and 1 <= day <= 31 and 2020 <= year <= 2035:
                return datetime(year, month, day)
        except Exception:
            return None
        return None

    def _categorize_date_type(self, text_context: str) -> str:
        upper = text_context.upper()
        if re.search(r'(?:^|[^A-Z])(EXP|EXPIRY|USE\s*BY|USE\s*BEFORE|CONSUME\s*BEFORE|UB)(?:$|[^A-Z])', upper):
            return "EXPIRY"
        elif re.search(r'(?:^|[^A-Z])(BEST\s*BEFORE|BEST\s*BY|BEST\s*IF\s*USED\s*BY|BB|B\.B\.)(?:$|[^A-Z])', upper):
            return "BEST_BEFORE"
        elif re.search(r'(?:^|[^A-Z])(MFG|MFD|PKD|PACKED|PACKING|DATE\s*OF\s*MFG|DOM|DOP)(?:$|[^A-Z])', upper):
            return "MANUFACTURING"
        return "UNKNOWN"

    def process_image(self, image_path: str, product_item: str = "packaged_milk") -> Dict[str, Any]:
        if not os.path.exists(image_path):
            return {
                "success": False,
                "extracted_date": None,
                "detected_text": "Image file not found",
                "confidence": 0.0,
                "date_type": "UNKNOWN",
                "date_status": "Uncertain",
                "is_estimated": False,
                "needs_manual_check": True
            }

        img_bgr = cv2.imread(image_path)
        if img_bgr is None:
            return {
                "success": False,
                "extracted_date": None,
                "detected_text": "Failed to decode image",
                "confidence": 0.0,
                "date_type": "UNKNOWN",
                "date_status": "Uncertain",
                "is_estimated": False,
                "needs_manual_check": True
            }

        if self.ocr is None:
            return {
                "success": False,
                "extracted_date": None,
                "detected_text": "OCR engine unavailable",
                "confidence": 0.0,
                "date_type": "UNKNOWN",
                "date_status": "Uncertain",
                "is_estimated": False,
                "needs_manual_check": True
            }

        variants = self._preprocess_variants(img_bgr)
        candidate_detections = []
        all_detected_lines = []

        for v_idx, var_img in enumerate(variants):
            try:
                res, _ = self.ocr(var_img)
            except Exception as e:
                logger.debug(f"OCR run on variant {v_idx} failed: {e}")
                res = None

            if not res:
                continue

            # Assemble word tokens into lines
            assembled_lines = self._assemble_lines(res)
            all_detected_lines = [l[0] for l in assembled_lines]

            for idx, (line_text, score) in enumerate(assembled_lines):
                upper = line_text.upper()

                # 1. First priority: full 3-part dates
                matched = False
                for r_pat in FULL_DATE_REGEXES:
                    match = re.search(r_pat, upper)
                    if match:
                        parsed_dt = self._parse_matched_date(match)
                        if parsed_dt:
                            dtype = self._categorize_date_type(upper)
                            # Check neighboring lines if current line lacks keyword
                            if dtype == "UNKNOWN":
                                if idx > 0:
                                    prev_text = assembled_lines[idx - 1][0]
                                    dtype = self._categorize_date_type(prev_text)
                                if dtype == "UNKNOWN" and idx < len(assembled_lines) - 1:
                                    next_text = assembled_lines[idx + 1][0]
                                    dtype = self._categorize_date_type(next_text)

                            candidate_detections.append({
                                "date": parsed_dt,
                                "raw_text": line_text,
                                "date_type": dtype,
                                "confidence": score
                            })
                            matched = True
                            break

                # 2. Secondary priority: 2-part month-year dates (only if no full date matched)
                if not matched:
                    for r_pat in MONTH_YEAR_REGEXES:
                        match = re.search(r_pat, upper)
                        if match:
                            parsed_dt = self._parse_matched_date(match)
                            if parsed_dt:
                                dtype = self._categorize_date_type(upper)
                                if dtype == "UNKNOWN":
                                    if idx > 0:
                                        dtype = self._categorize_date_type(assembled_lines[idx - 1][0])
                                    if dtype == "UNKNOWN" and idx < len(assembled_lines) - 1:
                                        dtype = self._categorize_date_type(assembled_lines[idx + 1][0])

                                candidate_detections.append({
                                "date": parsed_dt,
                                "raw_text": line_text,
                                "date_type": dtype,
                                "confidence": score * 0.90
                            })
                            break

            if candidate_detections:
                break

        if not candidate_detections:
            return {
                "success": False,
                "extracted_date": None,
                "detected_text": "No printed date found on label",
                "confidence": 0.0,
                "date_type": "UNKNOWN",
                "date_status": "Uncertain",
                "is_estimated": False,
                "needs_manual_check": True,
                "raw_lines": all_detected_lines
            }

        expiry_candidates = [c for c in candidate_detections if c["date_type"] in ["EXPIRY", "BEST_BEFORE"]]
        mfg_candidates = [c for c in candidate_detections if c["date_type"] == "MANUFACTURING"]

        shelf_days = DAIRY_SHELF_LIFE_DAYS.get(product_item.lower(), 7)

        if expiry_candidates:
            best = max(expiry_candidates, key=lambda x: x["confidence"])
            final_type = best["date_type"]
            final_date = best["date"]
            is_estimated = False
        elif mfg_candidates:
            # Manufacturing date found: DO NOT treat MFG as expiry date!
            best = max(mfg_candidates, key=lambda x: x["confidence"])
            mfg_date = best["date"]
            final_date = mfg_date + timedelta(days=shelf_days)
            final_type = "ESTIMATED_FROM_MFG"
            is_estimated = True
            logger.info(f"MFG date {mfg_date.strftime('%Y-%m-%d')} detected. Estimated expiry: {final_date.strftime('%Y-%m-%d')} (+{shelf_days}d).")
        else:
            best = max(candidate_detections, key=lambda x: x["confidence"])
            final_date = best["date"]
            final_type = best["date_type"]
            is_estimated = False

        today = datetime.now(timezone.utc).date()
        target_d = final_date.date()

        if target_d < today:
            status = "Expired"
        elif target_d <= today + timedelta(days=3):
            status = "Expiring Soon"
        else:
            status = "Fresh"

        conf = round(best["confidence"], 3)
        needs_check = (conf < 0.60) or (final_type == "UNKNOWN") or is_estimated

        return {
            "success": True,
            "extracted_date": final_date.strftime("%Y-%m-%d"),
            "original_parsed_date": final_date,
            "detected_text": best["raw_text"],
            "confidence": conf,
            "date_type": final_type,
            "date_status": status,
            "is_estimated": is_estimated,
            "estimated_rule_days": shelf_days if is_estimated else None,
            "needs_manual_check": needs_check,
            "raw_lines": all_detected_lines
        }

ocr_engine = DairyExpiryOCREngine()

def extract_expiry_date(image_path: str, product_item: str = "packaged_milk") -> Tuple[Optional[datetime], str, float]:
    res = ocr_engine.process_image(image_path, product_item)
    if res["success"]:
        return res["original_parsed_date"], res["detected_text"], res["confidence"]
    return None, res["detected_text"], 0.0
