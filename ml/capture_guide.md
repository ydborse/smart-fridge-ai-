# Field Capture Guide: Smart Fridge Freshness Dataset Collection

This guide outlines protocol for photographing fruits and vegetables throughout their lifecycle inside and outside a refrigerator to train high-accuracy freshness classification and detection models.

---

## 1. Target Items & Lifecycles

Our model predicts **9 items** across **4 freshness stages**:

| Item | Focus Attributes | Fresh | Ripe | Overripe | Rotten |
|---|---|---|---|---|---|
| **Apple** | Skin firmness, gloss, bruising | Crisp, firm, uniform skin | Slight softening, vibrant color | Wrinkling, brown soft spots | Soft rot, fungal mold, collapsed skin |
| **Banana** | Peel coloring, brown speckling | Green to vibrant yellow, firm stem | Yellow with minor sugar spots | Heavily brown/blackened peel, soft | Liquefying, moldy stem, sour smell |
| **Strawberry** | Calyx greenness, seed depression, fur | Bright red, crisp green leaves | Deep red, glossy, sweet scent | Darkened red, wilting leaves, weeping | Grey mold (*Botrytis*), fuzzy spots |
| **Tomato** | Turgidity, stem scar integrity | Smooth, taut, firm skin | Full uniform red, yielding gently | Deep wrinkling, mushy indentations | Split skin, leakage, black mold spots |
| **Capsicum** | Wall firmness, stem moisture | Rigid, glossy, crisp wall | Vivid coloration, slight give | Loss of turgor, shriveling ridges | Soft translucent rot, mold inside cavity |
| **Green Chilli** | Gloss, stem crispness, tip drying | Firm, vibrant green, snappy | Darkening green to reddish blush | Dry, shriveled, brittle skin | Blackening, slimy tip, grey rot |
| **Coriander** | Leaf crispness, stem rigidity, yellowing | Crisp upright green leaves | Dark green, slight limpness | Yellowing leaves, wilting stems | Black slimy decomposition, odor |
| **Carrot** | Root firmness, tip moisture | Extremely rigid, vibrant orange | Mild flexibility, pale orange | Bending, wrinkling, rubbery texture | Black rot, white fungal fuzz |
| **Lychee** | Shell color, bumps, aril moisture | Pink/red rough rind, firm | Deep red/maroon shell | Brownish brittle shell, dry | Dark brown/black cracked shell, mold |

---

## 2. Setup & Lighting Conditions

### Refrigerator Interior
- Capture under internal LED lighting (warm white and cool white).
- Position items on different shelves (wire rack, tempered glass shelf, crisper drawer).
- Test with door ajar at varying angles (shadows and ambient room light mixing).

### External Countertop
- Direct sunlight, diffused daytime window light, and artificial fluorescent/LED kitchen bulbs.
- Solid background (white chopping board, wooden counter, stainless steel prep table).

---

## 3. Angle & Composition Protocols

1. **Top-Down (Bird’s Eye 90°)**:
   - Full silhouette and leaf/stem condition (essential for coriander and chillies).
2. **Angled (45° Perspective)**:
   - Simulates typical user holding phone while looking into a fridge shelf.
3. **Close-Up Texture (Macro / High Res)**:
   - Captures skin micro-wrinkles, seed depressions, and early fungal spores.
4. **Occlusion & Clutter**:
   - Items partially tucked behind containers, cartons, or bagged produce.

---

## 4. Daily Longitudinal Time-Lapse Tracking

To build true continuous freshness curves:
1. Purchase fresh batches from farmer markets or grocery stores.
2. Photograph each sample at **identical times daily (e.g. 10:00 AM)** until full decomposition.
3. Keep one set refrigerated (2-5°C) and one set at room temperature (22-25°C) to train temperature decay gradients.

---

## 5. Storage and File Naming

Save raw photos in the following format:
```
dataset/raw/{item_name}/{freshness_class}/{item}_{YYYYMMDD_HHMM}_{camera_id}_{idx}.jpg
```
Example:
`dataset/raw/coriander/rotten/coriander_20261004_1015_phone_003.jpg`
