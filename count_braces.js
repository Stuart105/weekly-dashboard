var fs=require('fs');
var html=fs.readFileSync('D:/workbuddykongjian/2026-06-11-10-36-28/weekly-dashboard.html','utf8');
var match=html.match(/<script>([\s\S]*?)<\/script>/);
var code=match[1].trim();
// Replace DATA JSON with stub
var dataStart=code.indexOf('const DATA = ');
var afterData=code.substring(dataStart+13);
var b=0, end=-1;
for(var i=0;i<afterData.length;i++){
  if(afterData[i]==='{') b++;
  if(afterData[i]==='}'){ b--; if(b===0){ end=i+1; break; } }
}
var rest=code.substring(0,dataStart)+'const DATA = {};'+code.substring(dataStart+13+end+2);
// Count
var bo=0,bc=0,po=0,pc=0,bt=0;
for(var i=0;i<rest.length;i++){
  if(rest[i]==='{') bo++;
  if(rest[i]==='}') bc++;
  if(rest[i]==='(') po++;
  if(rest[i]===')') pc++;
  if(rest[i]==='`') bt++;
}
console.log('Braces:  {'+bo+'  }'+bc+'  diff='+(bo-bc));
console.log('Parens:  ('+po+'  )'+pc+'  diff='+(po-pc));
console.log('Backticks: '+bt+' (even? '+(bt%2===0)+')');

// Now try to find the missing brace/paren
var lineCount=0, braceCount=0;
var lines=rest.split('\n');
for(var i=0;i<lines.length;i++){
  var line=lines[i];
  for(var j=0;j<line.length;j++){
    if(line[j]==='{') braceCount++;
    if(line[j]==='}') braceCount--;
  }
  // Skip template literals and strings
  if(i===lines.length-10) console.log('Last 10 lines: braceCount='+braceCount);
  console.log('L'+(i+1)+': depth='+braceCount+' '+line.substring(0,80));
}
