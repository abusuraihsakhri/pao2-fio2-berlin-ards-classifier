import { assess, parseCSV, toCSV } from "./calculator.mjs";
const form = document.getElementById("assessment");
const ids = ["pao2","fio2","peep","paco2","map","age","spo2","patm"];
let current = null;
let batch = null;
const el = id => document.getElementById(id);
const fmt = value => Number(value).toFixed(1);
function inputs() { return Object.fromEntries(ids.map(id => [id, el(id).value])); }
function downloadFile(contents, name, mime) {
  const url = URL.createObjectURL(new Blob([contents], {type:mime}));
  const a = document.createElement("a");
  a.href=url; a.download=name; document.body.appendChild(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 2000);
}
function clearResults() {
  current = null;
  el("pf").textContent = "—";
  el("category").textContent = "Enter measurements and calculate";
  el("metrics").replaceChildren();
  el("warnings").replaceChildren();
  el("download").disabled = true;
}
function render(result) {
  el("pf").textContent = fmt(result.pf);
  el("category").textContent = result.category;
  const metrics = [
    ["PEEP criterion (≥5 cmH₂O)", result.peepCriteriaMet ? "Recorded as met" : "Not established"]
  ];
  if (result.aaGradient !== undefined) metrics.push(["A–a gradient (mmHg)", fmt(result.aaGradient)]);
  if (result.oxygenationIndex !== undefined) metrics.push(["Oxygenation index", fmt(result.oxygenationIndex)]);
  if (result.ageExpectedAA !== undefined) metrics.push(["Age-based expected A–a (room-air heuristic)", fmt(result.ageExpectedAA)]);
  if (result.sf !== undefined) metrics.push(["SpO₂/FiO₂ ratio", fmt(result.sf)]);
  const fragment = document.createDocumentFragment();
  for (const [name,value] of metrics) {
    const dt = document.createElement("dt"); dt.textContent=name;
    const dd = document.createElement("dd"); dd.textContent=value;
    fragment.append(dt, dd);
  }
  el("metrics").replaceChildren(fragment);
  const items = result.warnings.map(message => {
    const li=document.createElement("li");
    li.textContent=message;
    return li;
  });
  el("warnings").replaceChildren(...items);
  el("download").disabled=false;
}
form.addEventListener("submit", event => {
  event.preventDefault();
  try {
    const values = inputs();
    const result = assess(values);
    current = { inputs:values, calculations:result, interpretiveNote:"Berlin oxygenation range only; not a diagnosis" };
    render(result);
    el("error").textContent="";
  } catch (error) {
    clearResults();
    el("error").textContent=error.message;
  }
});
el("example").addEventListener("click", () => {
  const example = {pao2:"60",fio2:"0.4",peep:"8",paco2:"42",map:"15",age:"55",spo2:"94",patm:"760"};
  for (const id of ids) el(id).value=example[id];
  form.requestSubmit();
});
form.addEventListener("reset", () => {
  // reset fires before the browser restores input defaults
  clearResults(); el("error").textContent="";
});
el("download").addEventListener("click", () => {
  if (current) downloadFile(JSON.stringify(current,null,2)+"\n","berlin-oxygenation-result.json","application/json");
});
el("csv").addEventListener("change", async event => {
  batch = null;
  el("download-csv").disabled = true;
  el("batch-error").textContent="";
  el("batch-status").textContent="";
  const file = event.target.files && event.target.files[0];
  if (!file) return;
  try {
    if (file.size > 5 * 1024 * 1024) throw new Error("CSV exceeds 5 MB limit.");
    const rows = parseCSV(await file.text());
    if (rows.length > 10000) throw new Error("CSV exceeds 10,000 rows.");
    if (!rows.length) throw new Error("No data rows were found.");
    batch = rows.map((row, i) => {
      try {
        const result=assess(row);
        const out={patient_id:row.patient_id || "",pf_ratio:fmt(result.pf),
          severity:result.category,meets_peep_criteria:String(result.peepCriteriaMet),
          a_a_gradient:result.aaGradient === undefined ? "" : fmt(result.aaGradient),
          oxygenation_index:result.oxygenationIndex === undefined ? "" : fmt(result.oxygenationIndex),
          spo2_fio2_ratio:result.sf === undefined ? "" : fmt(result.sf),
          warnings:result.warnings.join("; ")};
        return out;
      } catch (error) {
        throw new Error("Row "+(i+2)+": "+error.message);
      }
    });
    el("batch-status").textContent = batch.length + " records classified locally. Download the CSV to save results.";
    el("download-csv").disabled=false;
  } catch (error) {
    batch=null;
    el("batch-error").textContent=error.message;
  }
});
el("download-csv").addEventListener("click",()=>{
  if (batch && batch.length) downloadFile(toCSV(batch),"berlin-oxygenation-results.csv","text/csv;charset=utf-8");
});
clearResults();
