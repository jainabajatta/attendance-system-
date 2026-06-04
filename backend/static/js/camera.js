/**
 * Camera and Face Detection Module
 */

class CameraManager {
    constructor(videoElement, canvasElement = null) {
        this.video = videoElement;
        this.canvas = canvasElement;
        this.stream = null;
        this.ws = null;
        this.isProcessing = false;
        this.onFrameProcessed = null;
        this.onFaceDetected = null;
    }
    
    async initCamera(width = 640, height = 480) {
        try {
            this.stream = await navigator.mediaDevices.getUserMedia({
                video: {
                    width: { ideal: width },
                    height: { ideal: height },
                    facingMode: 'user'
                }
            });
            
            this.video.srcObject = this.stream;
            await this.video.play();
            
            if (this.canvas) {
                this.canvas.width = this.video.videoWidth;
                this.canvas.height = this.video.videoHeight;
            }
            
            return true;
        } catch (error) {
            console.error('Camera initialization error:', error);
            throw new Error('Unable to access camera');
        }
    }
    
    initWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        this.ws = new WebSocket(`${protocol}//${window.location.host}/ws/recognize`);
        
        this.ws.onopen = () => {
            console.log('WebSocket connected');
            this.isProcessing = true;
            this.startProcessing();
        };
        
        this.ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            if (data.type === 'recognition' && this.onFrameProcessed) {
                this.onFrameProcessed(data.faces);
                
                if (this.onFaceDetected && data.faces.length > 0) {
                    this.onFaceDetected(data.faces);
                }
            }
        };
        
        this.ws.onerror = (error) => {
            console.error('WebSocket error:', error);
            this.isProcessing = false;
        };
        
        this.ws.onclose = () => {
            console.log('WebSocket disconnected');
            this.isProcessing = false;
        };
    }
    
    startProcessing() {
        if (!this.isProcessing || !this.ws || this.ws.readyState !== WebSocket.OPEN) {
            return;
        }
        
        const processFrame = () => {
            if (!this.isProcessing || !this.video.videoWidth) {
                requestAnimationFrame(processFrame);
                return;
            }
            
            // Capture frame
            const tempCanvas = document.createElement('canvas');
            tempCanvas.width = this.video.videoWidth;
            tempCanvas.height = this.video.videoHeight;
            const tempCtx = tempCanvas.getContext('2d');
            tempCtx.drawImage(this.video, 0, 0);
            
            // Send to server
            const frameData = tempCanvas.toDataURL('image/jpeg', 0.8);
            if (this.ws.readyState === WebSocket.OPEN) {
                this.ws.send(frameData);
            }
            
            requestAnimationFrame(processFrame);
        };
        
        processFrame();
    }
    
    stopProcessing() {
        this.isProcessing = false;
        if (this.ws) {
            this.ws.close();
        }
        if (this.stream) {
            this.stream.getTracks().forEach(track => track.stop());
        }
    }
    
    captureSnapshot() {
        if (!this.video.videoWidth) return null;
        
        const canvas = document.createElement('canvas');
        canvas.width = this.video.videoWidth;
        canvas.height = this.video.videoHeight;
        const ctx = canvas.getContext('2d');
        ctx.drawImage(this.video, 0, 0);
        
        return canvas.toDataURL('image/jpeg', 0.9);
    }
    
    async captureMultipleSnapshots(count, interval = 500) {
        const snapshots = [];
        
        for (let i = 0; i < count; i++) {
            const snapshot = this.captureSnapshot();
            if (snapshot) {
                snapshots.push(snapshot);
            }
            await new Promise(resolve => setTimeout(resolve, interval));
        }
        
        return snapshots;
    }
}

class FaceOverlay {
    constructor(canvasElement) {
        this.canvas = canvasElement;
        this.ctx = canvasElement.getContext('2d');
        this.faces = [];
    }
    
    drawFaces(faces) {
        this.clear();
        
        faces.forEach(face => {
            const [x, y, w, h] = face.bbox;
            const confidence = face.confidence;
            const isRecognized = confidence > 65;
            
            // Draw bounding box
            this.ctx.strokeStyle = isRecognized ? '#00ff00' : '#ffaa00';
            this.ctx.lineWidth = 3;
            this.ctx.strokeRect(x, y, w, h);
            
            // Draw label background
            const labelText = `${face.name} (${confidence.toFixed(1)}%)`;
            this.ctx.font = '14px Arial';
            const textWidth = this.ctx.measureText(labelText).width;
            
            this.ctx.fillStyle = 'rgba(0, 0, 0, 0.7)';
            this.ctx.fillRect(x, y - 25, textWidth + 20, 25);
            
            // Draw label text
            this.ctx.fillStyle = isRecognized ? '#00ff00' : '#ffaa00';
            this.ctx.fillText(labelText, x + 5, y - 8);
            
            // Draw confidence bar
            const barWidth = (confidence / 100) * w;
            this.ctx.fillStyle = isRecognized ? 'rgba(0, 255, 0, 0.3)' : 'rgba(255, 170, 0, 0.3)';
            this.ctx.fillRect(x, y + h + 5, barWidth, 5);
            
            // Draw animation effect for recognized faces
            if (isRecognized) {
                this.ctx.beginPath();
                this.ctx.arc(x + w / 2, y + h / 2, 5, 0, 2 * Math.PI);
                this.ctx.fillStyle = '#00ff00';
                this.ctx.fill();
            }
        });
    }
    
    clear() {
        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
    }
    
    resize(width, height) {
        this.canvas.width = width;
        this.canvas.height = height;
    }
}

// Export modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { CameraManager, FaceOverlay };
}
