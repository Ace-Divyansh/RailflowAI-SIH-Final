// ===================================================================
// DEFINITIVE sketch.js for Advanced Station Simulation
// ===================================================================

// --- Global Variables ---
let simData = null;
let trains = {};
let points = {};
let signals = {};
let animationTime = 0;
let maxTime = 0;
let isAnimating = false;
let isPaused = false;
const viz = document.getElementById('visualization');

// --- P5.js Setup (runs once at the start) ---
function setup() {
    noCanvas(); // We are using HTML/CSS for visuals, not the p5 canvas
    frameRate(60); // Run at a smooth 60fps
    
    // Attach event listeners to the buttons
    document.getElementById('naiveButton').addEventListener('click', () => startSimulation('/get_naive_sim_data', 'Naive Controller'));
    document.getElementById('aiButton').addEventListener('click', () => startSimulation('/get_ai_sim_data', 'AI Controller'));
    document.getElementById('pauseButton').addEventListener('click', togglePause);
}

// --- Control Functions ---
async function startSimulation(url, mode) {
    console.log(`Fetching data from ${url}...`);
    document.getElementById('modeText').innerText = `Loading...`;
    isAnimating = false; // Stop any current animation

    try {
        const response = await fetch(url);
        simData = await response.json();

        if (simData.error) {
            alert(`Server Error: ${simData.error}`);
            document.getElementById('modeText').innerText = `Error!`;
            return;
        }
        
        // --- Initialize the simulation scene ---
        viz.innerHTML = ''; // Clear previous elements
        createTracks();
        createPoints();
        createSignals();
        createTrains();
        
        maxTime = simData.events[simData.events.length - 1].time;
        animationTime = 0;
        isAnimating = true;
        document.getElementById('modeText').innerText = mode;
        if (isPaused) togglePause(); // Unpause if the new sim is started while paused
        loop(); // Start the p5.js draw loop
    } catch (error) {
        console.error("Failed to fetch or process simulation data:", error);
        alert("An error occurred. Check the console for details.");
    }
}

function togglePause() {
    isPaused = !isPaused;
    if (isPaused) {
        noLoop(); // Pauses the draw loop
    } else {
        loop(); // Resumes the draw loop
    }
}

// --- P5.js Draw Loop (The Animation Engine) ---
function draw() {
    if (!isAnimating) return;

    // --- State Calculation ---
    let trackStates = {}; // Stores occupancy of each track segment
    let pointStates = {}; // Stores position of each point

    simData.events.forEach(event => {
        if (event.time <= animationTime) {
            // Update the internal state of trains and points based on the log
            updateInternalState(event, pointStates);
        }
    });

    // Animate each train's visual position and determine track occupancy
    for (const trainId in trains) {
        animateTrain(trains[trainId]);
        const train = trains[trainId];
        if (train.active_track) {
            trackStates[train.active_track] = true;
        }
    }
    
    // Update visuals for points and signals based on the calculated states
    updatePoints(pointStates);
    updateSignals(trackStates, pointStates);
    
    // Update the time display on the UI
    document.getElementById('timeText').innerText = animationTime.toFixed(2);
    
    // Increment animation time
    animationTime += 0.2; // Adjust this value to change animation speed
    if (animationTime > maxTime) {
        isAnimating = false;
        noLoop(); // Stop the loop when the simulation is over
    }
}


// --- Logic and Animation Helper Functions ---
function updateInternalState(event, pointStates) {
    const train = trains[event.train_id];
    if (!train) return;
    
    if (event.event === 'spawned') {
        train.state = 'active';
        train.current_route = event.details.route;
    }
    if (event.event === 'enter_track') {
        train.active_track = event.details.track;
        train.startTime = event.time;
    }
    if (event.event === 'points_set') {
        event.details.points.forEach(p => pointStates[p] = event.details.state);
    }
    if (event.event === 'finished') {
        train.state = 'inactive';
        train.active_track = null;
    }
}

function animateTrain(train) {
    if (train.state === 'inactive') {
        train.element.style.opacity = '0';
        return;
    }
    train.element.style.opacity = '1';

    // This is a simplified animation mapping track names to coordinates.
    // A more advanced version would calculate paths along curves.
    const trackPositions = {
        'L2_Approach': { x: 150, y: 100 },
        'L1_Platform_2': { x: 450, y: 50 },
        'L2_Exit': { x: 750, y: 100 },
        'L3_Approach': { x: 150, y: 250 },
        'L4_Platform_1': { x: 450, y: 300 },
        'L5_Siding': { x: 750, y: 350 },
        'L3_Exit': { x: 750, y: 250 },
    };
    
    const pos = trackPositions[train.active_track];
    if (pos) {
        train.element.style.left = `${pos.x - 25}px`;
        train.element.style.top = `${pos.y - 12.5}px`;
    }
}

function updatePoints(pointStates) {
    for (const pointId in pointStates) {
        const pointEl = document.getElementById(`point-${pointId}`);
        if(pointEl) {
            const angle = pointStates[pointId] === 'reverse' ? (pointEl.dataset.angle || 0) : 0;
            pointEl.style.transform = `rotate(${angle}deg)`;
        }
    }
}

function updateSignals(trackStates, pointStates) {
    // A simplified interlocking logic for visualization
    for (const signalId in signals) {
        const signal = signals[signalId];
        const isOccupied = trackStates[signal.protects];
        signal.element.className = isOccupied ? 'signal red' : 'signal green';
    }
}


// --- HTML Element Creation Functions ---
function createTrains() {
    simData.schedule.forEach(t => {
        const trainDiv = document.createElement('div');
        trainDiv.id = `train-${t.train_id}`;
        trainDiv.className = `train ${t.direction}-train inactive`;
        trainDiv.innerText = t.train_id;
        viz.appendChild(trainDiv);
        trains[t.train_id] = { ...t, element: trainDiv, state: 'inactive', active_track: null };
    });
}

function createSignals() {
    // This maps signal IDs to their position and the track they protect
    const signalData = {
        'S1': { x: 270, y: 20, protects: 'L1_Platform_2'},
        'S2': { x: 180, y: 70, protects: 'L2_Approach'},
        'S3': { x: 600, y: 20, protects: 'L1_Platform_2'},
        'S4': { x: 750, y: 70, protects: 'L2_Exit'},
        'S5': { x: 100, y: 220, protects: 'L3_Approach'},
        'S6': { x: 300, y: 270, protects: 'L4_Platform_1'},
        'S7': { x: 800, y: 220, protects: 'L3_Exit'},
        'S8': { x: 580, y: 270, protects: 'L4_Platform_1'},
        'S9': { x: 650, y: 320, protects: 'L5_Siding'},
        'S10': { x: 800, y: 320, protects: 'L5_Siding'},
    };
     for (const id in signalData) {
        const signalDiv = document.createElement('div');
        signalDiv.id = `signal-${id}`;
        signalDiv.className = 'signal green';
        signalDiv.style.left = `${signalData[id].x}px`;
        signalDiv.style.top = `${signalData[id].y}px`;
        viz.appendChild(signalDiv);
        signals[id] = { element: signalDiv, protects: signalData[id].protects };
    }
}

function createPoints() {
    // Maps point IDs to their position and rotation angle for the 'reverse' state
    const pointData = {
        'P1': { x: 200, y: 100, angle: -45 },
        'P2': { x: 650, y: 100, angle: 45 },
        'P3': { x: 200, y: 250, angle: 45 },
        'P4': { x: 650, y: 250, angle: -45 },
        'PX1': { x: 450, y: 100, angle: 45 },
        'PX2': { x: 450, y: 250, angle: -45 },
        'P5': { x: 600, y: 300, angle: 45 },
    };
    for (const id in pointData) {
        const pointDiv = document.createElement('div');
        pointDiv.id = `point-${id}`;
        pointDiv.className = 'point';
        pointDiv.style.left = `${pointData[id].x}px`;
        pointDiv.style.top = `${pointData[id].y}px`;
        pointDiv.style.width = '50px';
        pointDiv.dataset.angle = pointData[id].angle;
        viz.appendChild(pointDiv);
        points[id] = { element: pointDiv };
               if (id === 'P2') {
            pointDiv.style.width = '50px'; // Make P1 longer
            pointDiv.style.transformOrigin = 'right'; // Make it rotate from the left
        }
         else if(id==='P4'){
            pointDiv.style.transformOrigin = 'right';
        }
        else{
            pointDiv.style.transformOrigin = 'left';
        }
        
        viz.appendChild(pointDiv);
        points[id] = { element: pointDiv };
    }
    }


function createTracks() {
    // A simplified visual representation of your 5-line schematic
    const trackHTML = `
        <div class="track" style="top: 100px; width: 900px; left: 0;"></div> <!-- L2 UP MAIN -->
        <div class="track" style="top: 50px; width: 400px; left: 250px;"></div> <!-- L1 UP PLATFORM -->
        <div class="track" style="top: 250px; width: 900px; left: 0;"></div> <!-- L3 DOWN MAIN -->
        <div class="track" style="top: 300px; width: 400px; left: 250px;"></div> <!-- L4 DOWN PLATFORM -->
        <div class="track" style="top: 350px; width: 400px; left: 500px;"></div> <!-- L5 DOWN SIDING -->
    `;
    viz.innerHTML = trackHTML;
}

