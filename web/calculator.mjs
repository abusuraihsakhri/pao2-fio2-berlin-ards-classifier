/**
 * Deterministic browser calculations; no network, cookies, or persistent storage.
 * Berlin (2012) oxygenation ranges do not establish an ARDS diagnosis.
 */
function finite(name, value, min = -Infinity, max = Infinity, inclusiveMin = true) {
  if (typeof value !== "number" || !Number.isFinite(value) ||
      (inclusiveMin ? value < min : value <= min) || value > max) {
    throw new RangeError(name + " must be finite and within the allowed range.");
  }
}
function optionalNumber(value) {
  return value === "" || value === null || value === undefined ? null : Number(value);
}
export function assess(inputs) {
  if (inputs.pao2 === "" || inputs.pao2 === null || inputs.pao2 === undefined ||
      inputs.fio2 === "" || inputs.fio2 === null || inputs.fio2 === undefined) {
    throw new RangeError("PaO2 and FiO2 are required.");
  }
  const pao2 = Number(inputs.pao2);
  const fio2 = Number(inputs.fio2);
  const peep = optionalNumber(inputs.peep);
  const paco2 = optionalNumber(inputs.paco2);
  const map = optionalNumber(inputs.map);
  const age = optionalNumber(inputs.age);
  const spo2 = optionalNumber(inputs.spo2);
  const patm = inputs.patm === "" || inputs.patm == null ? 760 : Number(inputs.patm);
  finite("PaO2 (mmHg)", pao2, 0);
  finite("FiO2 (fraction)", fio2, 0, 1, false);
  finite("Atmospheric pressure (mmHg)", patm, 47, Infinity, false);
  if (peep !== null) finite("PEEP (cmH2O)", peep, 0);
  if (paco2 !== null) finite("PaCO2 (mmHg)", paco2, 0);
  if (map !== null) finite("Mean airway pressure (cmH2O)", map, 0);
  if (age !== null) finite("Age (years)", age, 0, 130);
  if (spo2 !== null) finite("SpO2 (%)", spo2, 0, 100);

  const pf = pao2 / fio2;
  const category = pf > 300 ? "Outside ARDS oxygenation range" :
    pf > 200 ? "Mild oxygenation range" :
    pf > 100 ? "Moderate oxygenation range" : "Severe oxygenation range";
  const warnings = [];
  if (peep === null) warnings.push("Positive-pressure requirement cannot be checked: PEEP/CPAP was not provided.");
  else if (peep < 5) warnings.push("PEEP/CPAP is below 5 cmH2O; Berlin oxygenation criterion is not met.");
  warnings.push("Oxygenation alone does not diagnose ARDS. Verify onset, imaging, and origin of edema.");
  const result = {pf, category, peepCriteriaMet: peep !== null && peep >= 5, warnings};
  if (paco2 !== null) result.aaGradient = fio2 * (patm - 47) - paco2 / 0.8 - pao2;
  if (map !== null) {
    if (pao2 === 0) warnings.push("Oxygenation index is undefined at PaO2 = 0.");
    else result.oxygenationIndex = fio2 * map * 100 / pao2;
  }
  if (age !== null) {
    result.ageExpectedAA = age / 4 + 4;
    if (fio2 !== 0.21) warnings.push("Age-based expected A–a gradient is a room-air heuristic; do not use it to interpret supplemental oxygen measurements.");
  }
  if (spo2 !== null) {
    result.sf = spo2 / fio2;
    if (spo2 > 97) warnings.push("SpO2/FiO2 is not suitable for ARDS severity classification when SpO2 exceeds 97%.");
  }
  return result;
}
/** RFC 4180-style quoted CSV fields, escaped quotes, and line breaks. */
export function parseCSV(text) {
  const rows = [];
  let row = [], cell = "", quoted = false, closingQuote = false;
  text = String(text).replace(/^\uFEFF/, "");
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (quoted) {
      if (c === '"') {
        if (text[i + 1] === '"') { cell += '"'; i++; }
        else { quoted = false; closingQuote = true; }
      } else cell += c;
    } else if (c === ',' || c === '\n' || c === '\r') {
      row.push(cell); cell = ""; closingQuote = false;
      if (c !== ',') {
        if (row.some(value => value.length)) rows.push(row);
        row = [];
        if (c === '\r' && text[i + 1] === '\n') i++;
      }
    } else if (c === '"' && cell === "" && !closingQuote) quoted = true;
    else if (closingQuote) {
      if (c !== ' ' && c !== '\t') throw new Error("Unexpected characters after closing quote.");
    } else if (c === '"') throw new Error("Unexpected quote in unquoted field.");
    else cell += c;
  }
  if (quoted) throw new Error("Unclosed CSV quoted field.");
  row.push(cell);
  if (row.some(value => value.length)) rows.push(row);
  if (!rows.length) throw new Error("CSV is empty.");
  const headings = rows.shift().map(value => value.trim());
  if (new Set(headings).size !== headings.length) throw new Error("CSV headers must be unique.");
  for (const required of ["pao2", "fio2"]) {
    if (!headings.includes(required)) throw new Error("Missing CSV column: " + required);
  }
  return rows.map((values, index) => {
    if (values.length !== headings.length) throw new Error("CSV row " + (index + 2) + " has incorrect column count.");
    return Object.fromEntries(headings.map((heading, i) => [heading, values[i]]));
  });
}
export function toCSV(rows) {
  if (!rows.length) return "";
  const fields = Array.from(new Set(rows.flatMap(row => Object.keys(row))));
  function quote(value) {
    let s = String(value == null ? "" : value);
    // Prevent spreadsheet formula evaluation when data are exported and opened.
    if (/^[\s]*[=+\-@\t\r]/.test(s)) s = "'" + s;
    return '"' + s.replace(/"/g, '""') + '"';
  }
  return [fields.map(quote).join(","), ...rows.map(row => fields.map(field => quote(row[field])).join(","))].join("\r\n") + "\r\n";
}
