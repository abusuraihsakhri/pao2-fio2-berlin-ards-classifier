import test from 'node:test';
import assert from 'node:assert/strict';
import { assess, parseCSV, toCSV } from './calculator.mjs';

test('Berlin oxygenation cutoffs and pressure caveats', () => {
  for (const [pf,label] of [[100,"Severe"],[200,"Moderate"],[300,"Mild"],[301,"Outside"]]) {
    const result=assess({pao2:pf/2,fio2:0.5,peep:5});
    assert.match(result.category,new RegExp(label));
    assert.equal(result.peepCriteriaMet,true);
  }
  assert.equal(assess({pao2:60,fio2:0.4}).peepCriteriaMet,false);
});
test('validated physiology and derived metrics', () => {
  const r=assess({pao2:95,fio2:0.21,paco2:40,map:15,peep:10,age:20,spo2:94});
  assert.ok(Math.abs(r.aaGradient-4.73)<0.01);
  assert.ok(Math.abs(r.oxygenationIndex-3.315789)<0.01);
  assert.ok(Math.abs(r.ageExpectedAA-9)<0.001);
  for (const value of ["0","1.2","Infinity","NaN"]) {
    assert.throws(()=>assess({pao2:80,fio2:value}),RangeError);
  }
  assert.throws(()=>assess({pao2:"",fio2:"0.5"}),Error);
});
test('CSV parsing supports escaped quotes and quoted newlines', () => {
  const rows=parseCSV('pao2,fio2,patient_id\r\n80,0.5,"case ""1"""\r\n60,0.4,"case\n2"\r\n');
  assert.equal(rows.length,2);
  assert.equal(rows[0].patient_id,'case "1"');
  assert.equal(rows[1].patient_id,'case\n2');
});
test('CSV output prevents formula injection',()=>{
  const result=toCSV([{patient_id:'=HYPERLINK("https://invalid")',pf_ratio:'120'}]);
  assert.ok(result.includes(''=HYPERLINK'));
});
