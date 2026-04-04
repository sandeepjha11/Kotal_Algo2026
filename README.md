# Automated Options Trading Platform (Kotak Neo)

A full-featured browser-based automated options trading platform for NIFTY and SENSEX integrated with the Kotak Neo API.

## Features
- **Modern Dark Dashboard**: Real-time tracking of scheduled jobs, order configuration, and entry summary.
- **Trading Strategies**:
  - **Short Straddle**: Sells ATM Call & Put.
  - **Premium Based Strangle**: Selects strikes based on a target premium.
  - **Spot Based Strangle**: Selects OTM strikes based on a percentage from spot.
- **Scheduling**: Execute trades instantly or schedule them for a specific time (e.g., 09:20 AM).
- **Real-time Updates**: Position monitoring and MTM updates via WebSockets.

## Tech Stack
- **Frontend**: React, Tailwind CSS, Vite, Lucide React, Socket.io-client.
- **Backend**: Node.js, Express, Node-schedule, Socket.io.
- **API Bridge**: Python (Flask) using `neo-api-client` (Kotak Neo SDK).

## Prerequisites
- **Node.js**: v18 or higher.
- **Python**: v3.10 or higher.
- **Kotak Neo API Credentials**: Consumer Key, Mobile Number, UCC, MPIN, and TOTP Key.

## Setup Instructions

### 1. Clone the repository
```bash
# Navigate to the project directory
cd automated-trading-platform
```

### 2. Backend Setup (Node.js & Python)
Install Node.js dependencies:
```bash
cd server
npm install
```

Install Python dependencies:
```bash
pip install flask flask-cors neo-api-client pandas pyotp
```

### 3. Frontend Setup (React)
```bash
cd ../client
npm install
```

### 4. Configuration
Create a `.env` file in the root directory (use `.env.example` as a template):
```env
PORT=5000
PYTHON_BRIDGE_URL=http://localhost:5001
# Kotak Credentials can be provided via the Login screen or hardcoded in bridge for auto-login
```

## Running the Application

You only need to run two processes (the Backend will automatically start the Python Bridge for you).

### 1. Start the Node.js Backend
The backend manages strategy logic, scheduling, and automatically launches the Kotak Neo Python Bridge.
```bash
cd server
npm start
```
*Runs on http://localhost:5000 (Backend) and http://localhost:5001 (Bridge)*

### 2. Start the Frontend Dev Server
```bash
cd client
npm run dev
```
*Runs on http://localhost:5173*

## Usage
1. Open your browser and navigate to `http://localhost:5173`.
2. Login using your Kotak Neo credentials.
3. Use the **Order Configuration** panel to select your strategy, underlying index (NIFTY/SENSEX), lots, and stop-loss.
4. Click **Execute Strategy** to place orders immediately, or wait for scheduled jobs to trigger.
5. Monitor active trades in the **Entry Summary** panel.

## Project Structure
- `client/`: React frontend with Tailwind CSS.
- `server/index.js`: Main Express server handling logic and scheduling.
- `server/kotak_bridge.py`: Flask-based Python bridge for Kotak Neo API.
- `server/strategies.js`: Core trading strategy logic for strike selection.
