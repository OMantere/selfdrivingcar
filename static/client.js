var img = document.getElementById("liveImg");
var steeringText = document.getElementById("steering");
var throttleText = document.getElementById("throttle");
var ws = new WebSocket("ws://localhost:8002/");
ws.binaryType = 'arraybuffer';

function requestImage() {
    ws.send('more');
}

ws.onopen = function() {
    console.log("connection was established");
    requestImage();
};

function readDouble(buffer) {
    var view = new DataView(buffer);
    return view.getFloat64(0, true);
}

ws.onmessage = function(evt) {
    var arrayBuffer = evt.data;
    var imgBuffer = arrayBuffer.slice(0, -16)
    var throttle = readDouble(arrayBuffer.slice(-16, -8))
    var steering = readDouble(arrayBuffer.slice(-8))
    throttleText.textContent = parseFloat(throttle).toPrecision(2)
    steeringText.textContent = parseFloat(steering).toPrecision(2)
    var blob  = new Blob([new Uint8Array(imgBuffer)], {type: "image/jpeg"});
    img.src = window.URL.createObjectURL(blob);
    requestImage();
};
