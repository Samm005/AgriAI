function predict(){

const loader=document.getElementById("loader");
const resultBox=document.getElementById("resultBox");
const resultCard=document.getElementById("resultCard");

loader.style.display="block";
resultCard.style.display="none";

const email=localStorage.getItem("userEmail");

const data={
email:email,
SAVI:document.getElementById("SAVI").value,
Temperature:document.getElementById("Temperature").value,
Humidity:document.getElementById("Humidity").value,
Rainfall:document.getElementById("Rainfall").value,
Wind_Speed:document.getElementById("Wind_Speed").value,
Soil_Moisture:document.getElementById("Soil_Moisture").value,
Soil_pH:document.getElementById("Soil_pH").value,
Organic_Matter:document.getElementById("Organic_Matter").value,
Water_Flow:document.getElementById("Water_Flow").value,
NDVI:document.getElementById("NDVI").value
};

fetch("/predict",{
method:"POST",
headers:{"Content-Type":"application/json"},
body:JSON.stringify(data)
})
.then(res=>res.json())
.then(data=>{
loader.style.display="none";
resultCard.style.display="block";

let severityClass="low";
if(data.severity_level==="Medium") severityClass="medium";
if(data.severity_level==="High") severityClass="high";

resultBox.innerHTML=`
<div class="severity-badge ${severityClass}">${data.severity_level}</div>
<h3 class="stress-title">${data.stress_type}</h3>
<p><b>Confidence:</b> ${data.confidence}</p>
<p><b>Severity Score:</b> ${data.severity_score}</p>
<h4>Recommendations</h4>
${data.recommendations.map(r=>`<p class="rec">• ${r}</p>`).join("")}
`;
})
.catch(()=>{
loader.style.display="none";
});
}


if(document.getElementById("historyContainer")){

const email=localStorage.getItem("userEmail");

const welcome=document.getElementById("welcome");
const hour=new Date().getHours();
let greeting="";

if(hour<12) greeting="Good Morning 🌞";
else if(hour<17) greeting="Good Afternoon 🌤";
else if(hour<20) greeting="Good Evening 🌆";
else greeting="Good Night 🌙";

welcome.innerText=greeting;

fetch("/history/"+email)
.then(res=>res.json())
.then(data=>{

const container=document.getElementById("historyContainer");
container.innerHTML="";

data.forEach((item,index)=>{

if(!item.SAVI) return;

const card=document.createElement("div");
card.className="history-card";

let severityClass="low";
if(item.severity_level==="Medium") severityClass="medium";
if(item.severity_level==="High") severityClass="high";

const date=new Date(item.timestamp).toLocaleString();

card.innerHTML=`
<div class="severity-badge ${severityClass}">
${item.severity_level}
</div>
<h3 class="stress-title">${item.stress_type}</h3>
<p><b>Confidence:</b> ${item.confidence}</p>
<p><b>Date:</b> ${date}</p>
<div class="chart-wrapper">
<canvas id="chart${index}"></canvas>
</div>
`;

container.appendChild(card);

const ctx=document.getElementById(`chart${index}`);

new Chart(ctx,{
type:"pie",
data:{
labels:["SAVI","Temp","Humidity","Rainfall","Moisture","pH","Organic","Water Flow","NDVI"],
datasets:[{
data:[
Number(item.SAVI),
Number(item.Temperature),
Number(item.Humidity),
Number(item.Rainfall),
Number(item.Soil_Moisture),
Number(item.Soil_pH),
Number(item.Organic_Matter),
Number(item.Water_Flow),
Number(item.NDVI)
],
backgroundColor:[
"#3b82f6",
"#a855f7",
"#f59e0b",
"#ef4444",
"#06b6d4",
"#f472b6",
"#8b5cf6",
"#f97316",
"#22c55e"
],
borderWidth:2
}]
},
options:{
animation:{
animateRotate:true,
duration:1500
},
plugins:{
legend:{
labels:{color:"#fff"}
}
}
}
});

});
})
.catch(err=>{
console.log(err);
});
}