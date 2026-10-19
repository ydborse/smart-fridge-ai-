"""Live ML Training Demo - standalone and tiny.
Does not touch the main app, the webcam detector, Telegram alerts or any saved model.
The demo model lives in memory only and is thrown away when you stop the script."""
import base64
import io
import json
import threading
from pathlib import Path

import torch
import torch.nn as nn
import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from PIL import Image
from torchvision import models, transforms as T

EPOCHS, COPIES, STEPS = 15, 8, 3   # 15 epochs, 8 augmented copies per image, 3 updates per epoch
REPORT_PATHS = [
    Path(__file__).parent / "webcam_food_candidate_report.json",
    Path("/app/ml/reports/webcam_food_candidate_report.json"),
]
NORM = T.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])

app = FastAPI()
state = {"status": "idle", "epoch": 0, "epochs": EPOCHS, "log": []}
model = {}


def to_img(data_url):
    return Image.open(io.BytesIO(base64.b64decode(data_url.split(",", 1)[1]))).convert("RGB")


def train(items):
    try:
        state["log"].append("Loading pretrained MobileNetV2 (feature layers frozen)...")
        classes = sorted({l for _, l in items})
        imgs = [to_img(d) for d, _ in items]
        ys = [classes.index(l) for _, l in items]
        feat = models.mobilenet_v2(weights=models.MobileNet_V2_Weights.DEFAULT).features.eval()
        head = nn.Linear(1280, len(classes))          # the only part that is trained
        opt = torch.optim.Adam(head.parameters(), lr=0.001)
        lossf = nn.CrossEntropyLoss()
        aug = T.Compose([T.RandomResizedCrop(224, scale=(0.6, 1.0)), T.RandomHorizontalFlip(),
                         T.ColorJitter(0.3, 0.3, 0.3), T.ToTensor(), NORM])
        y = torch.tensor([c for c in ys for _ in range(COPIES)])
        state["log"].append(f"Training on {len(imgs)} images, classes: {classes}")
        for ep in range(EPOCHS):
            x = torch.stack([aug(im) for im in imgs for _ in range(COPIES)])
            with torch.no_grad():
                f = feat(x).mean([2, 3])
            for _ in range(STEPS):
                loss = lossf(head(f), y)
                opt.zero_grad()
                loss.backward()
                opt.step()
            state["epoch"] = ep + 1
            state["log"].append(f"Epoch {ep + 1}/{EPOCHS}   training loss = {loss.item():.4f}")
        model.update(feat=feat, head=head.eval(), classes=classes)
        state["log"].append("Training finished. Choose a test image below.")
        state["status"] = "done"
    except Exception as e:
        state["log"].append(f"Error: {e}")
        state["status"] = "error"


@app.post("/train")
async def train_ep(req: Request):
    if state["status"] == "training":
        return {"ok": False, "msg": "Already training"}
    items = [(i["img"], i["label"]) for i in (await req.json())["items"]]
    if len({l for _, l in items}) < 2:
        return {"ok": False, "msg": "Add images with at least 2 different labels"}
    state.update(status="training", epoch=0, log=[])
    threading.Thread(target=train, args=(items,), daemon=True).start()
    return {"ok": True}


@app.get("/status")
def status():
    return state


@app.post("/predict")
async def predict(req: Request):
    if not model:
        return {"ok": False, "msg": "Train the model first"}
    img = to_img((await req.json())["img"])
    x = NORM(T.ToTensor()(img.resize((224, 224)))).unsqueeze(0)
    with torch.no_grad():
        p = torch.softmax(model["head"](model["feat"](x).mean([2, 3])), 1)[0]
    i = int(p.argmax())
    return {"ok": True, "name": model["classes"][i], "conf": float(p[i])}


@app.get("/metrics")
def metrics():
    for p in REPORT_PATHS:
        if p.exists():
            r = json.loads(p.read_text())
            return {"ok": True, "n": r.get("num_test_samples"), "acc": r.get("test_accuracy"),
                    "classes": r.get("classes"), "report": r.get("classification_report")}
    return {"ok": False}


PAGE = r"""<!doctype html><meta charset=utf-8><title>Live ML Training Demo</title>
<style>
body{font-family:sans-serif;max-width:820px;margin:20px auto;padding:0 12px}
section{border:1px solid #ccc;border-radius:8px;padding:12px;margin:12px 0}
img.t{height:70px;border-radius:4px}
.bar{background:#eee;height:18px;border-radius:9px;overflow:hidden;margin:8px 0}
#fill{background:#2a9d4a;height:100%;width:0;transition:width .3s}
button{padding:6px 12px;margin:3px}
table{border-collapse:collapse}td,th{border:1px solid #ccc;padding:4px 10px;text-align:right}
td:first-child,th:first-child{text-align:left}
pre{background:#f6f6f6;padding:8px;max-height:220px;overflow:auto}
</style>
<h2>Live ML Training Demo</h2>

<section><b>1. Add labelled images</b> (2 or more different labels, 2-3 images is enough)<br>
Label: <input id=label placeholder="e.g. apple" list=l>
<datalist id=l><option>apple<option>banana<option>tomato<option>cucumber<option>mango<option>orange</datalist>
<input type=file id=files accept="image/*" multiple>
<br>or <button onclick=cam()>Start webcam</button><button onclick=snap()>Capture</button><br>
<video id=v autoplay playsinline width=240></video>
<div id=thumbs></div><button onclick="items=[];draw()">Clear images</button></section>

<section><b>2. Train</b><br><button onclick=train()>Train Model</button>
<div class=bar><div id=fill></div></div><pre id=log>Not trained yet.</pre></section>

<section><b>3. Test</b><br>
<input type=file id=tfile accept="image/*"> or <button onclick=tsnap()>Capture test image from webcam</button><br>
<img id=tprev height=120><br><button onclick=predict()>Predict</button>
<h3 id=res></h3></section>

<section><b>4. Existing model: held-out test set results</b> (read from the saved training report, not from the demo model)
<div id=met>Loading...</div></section>

<script>
const $=id=>document.getElementById(id);
let items=[],test=null;
const post=(u,b)=>fetch(u,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(b)}).then(r=>r.json());
function toData(el,w,h){const s=Math.min(1,320/Math.max(w,h));const c=document.createElement('canvas');c.width=w*s;c.height=h*s;const x=c.getContext('2d');x.fillStyle='#fff';x.fillRect(0,0,c.width,c.height);x.drawImage(el,0,0,c.width,c.height);return c.toDataURL('image/jpeg',0.9)}
function load(f){return new Promise(ok=>{const i=new Image();i.onload=()=>ok(toData(i,i.width,i.height));i.src=URL.createObjectURL(f)})}
async function cam(){try{$('v').srcObject=await navigator.mediaDevices.getUserMedia({video:true})}catch(e){alert('Webcam unavailable: '+e.message)}}
function frame(){const v=$('v');if(!v.videoWidth){alert('Click Start webcam first');return null}return toData(v,v.videoWidth,v.videoHeight)}
const lab=()=>$('label').value.trim().toLowerCase();
function add(d){items.push({img:d,label:lab()});draw()}
function snap(){if(!lab()){alert('Type a label first');return}const d=frame();if(d)add(d)}
$('files').onchange=async e=>{if(!lab()){alert('Type a label first');e.target.value='';return}for(const f of e.target.files)add(await load(f));e.target.value=''};
function draw(){$('thumbs').innerHTML=items.map(i=>`<figure style="display:inline-block;margin:4px"><img class=t src="${i.img}"><figcaption>${i.label}</figcaption></figure>`).join('')}
async function train(){
  const r=await post('/train',{items});if(!r.ok){alert(r.msg);return}
  const t=setInterval(async()=>{const s=await (await fetch('/status')).json();
    $('fill').style.width=(100*s.epoch/s.epochs)+'%';$('log').textContent=s.log.join('\n');
    if(s.status!='training')clearInterval(t)},500)}
function tsnap(){const d=frame();if(d){test=d;$('tprev').src=d}}
$('tfile').onchange=async e=>{if(e.target.files[0]){test=await load(e.target.files[0]);$('tprev').src=test}};
async function predict(){if(!test){alert('Choose a test image first');return}
  const r=await post('/predict',{img:test});$('res').textContent=r.ok?`${r.name} - ${(r.conf*100).toFixed(1)}% confidence`:r.msg}
fetch('/metrics').then(r=>r.json()).then(m=>{
  if(!m.ok){$('met').textContent='Report file not found, so no metrics are shown.';return}
  const row=(n,d)=>`<tr><td>${n}</td><td>${d.precision.toFixed(3)}</td><td>${d.recall.toFixed(3)}</td><td>${d['f1-score'].toFixed(3)}</td></tr>`;
  $('met').innerHTML=`<p>Test accuracy: <b>${(m.acc*100).toFixed(2)}%</b> on ${m.n} held-out test images</p><table><tr><th>class</th><th>precision</th><th>recall</th><th>F1</th></tr>${m.classes.map(c=>row(c,m.report[c])).join('')}${row('macro avg',m.report['macro avg'])}</table>`});
</script>"""


@app.get("/", response_class=HTMLResponse)
def index():
    return PAGE


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)