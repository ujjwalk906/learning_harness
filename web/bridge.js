/* An opaque activity frame can communicate only with its parent host. */
"use strict";
window.LearningHarness = Object.freeze({
  draft(payload) {parent.postMessage({channel:"learning-harness",type:"draft",payload},"*");},
  submit(payload) {parent.postMessage({channel:"learning-harness",type:"submit",payload},"*");},
  help(text) {parent.postMessage({channel:"learning-harness",type:"help",payload:{text}},"*");}
});
window.addEventListener("message",event=>{
  if(event.source===parent&&event.data?.channel==="learning-harness"&&event.data.type==="restore"){
    window.dispatchEvent(new CustomEvent("learning-harness-restore",{detail:event.data.payload}));
  }
});
const ready=()=>parent.postMessage({channel:"learning-harness",type:"ready"},"*");
if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",ready,{once:true});else ready();
