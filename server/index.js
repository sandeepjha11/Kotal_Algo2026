const express = require('express');
const cors = require('cors');
const axios = require('axios');
const http = require('http');
const { Server } = require('socket.io');
const schedule = require('node-schedule');
const dotenv = require('dotenv');
const { spawn } = require('child_process');
const path = require('path');
const strategies = require('./strategies');

dotenv.config();

const app = express();
app.use(cors());
app.use(express.json());

const server = http.createServer(app);
const io = new Server(server, {
  cors: { origin: "*", methods: ["GET", "POST"] }
});

const BRIDGE_URL = `http://localhost:${process.env.KOTAK_BRIDGE_PORT || 5001}`;

let bridgeProcess = null;
function startBridge() {
    console.log('Starting Kotak Bridge...');
    bridgeProcess = spawn('python', [path.join(__dirname, 'kotak_bridge.py')], {
        env: { ...process.env, KOTAK_BRIDGE_PORT: process.env.KOTAK_BRIDGE_PORT || 5001 }
    });
    bridgeProcess.stdout.on('data', (data) => {
        const str = data.toString();
        if (str.includes('INFO') || str.includes('200')) {
            console.log(`Bridge: ${str.trim()}`);
        } else {
            console.error(`Bridge Log: ${str.trim()}`);
        }
    });
    bridgeProcess.stderr.on('data', (data) => {
        const str = data.toString();
        if (str.includes('INFO') || str.includes('200')) {
            console.log(`Bridge: ${str.trim()}`);
        } else {
            console.error(`Bridge Error: ${str.trim()}`);
        }
    });
    bridgeProcess.on('close', (code) => {
        console.log(`Bridge process exited with code ${code}. Restarting...`);
        setTimeout(startBridge, 5000);
    });
}
startBridge();

let scheduledJobs = [];
let entrySummary = null;
let spotPrices = { NIFTY: '0.00', SENSEX: '0.00' };

// Periodic polling for MTM/Quotes
setInterval(async () => {
    if (entrySummary && entrySummary.details && entrySummary.details.ceStrike && entrySummary.details.peStrike) {
        try {
            const { ceStrike, peStrike, ceEntry, peEntry, quantity } = entrySummary.details;
            const quotesRes = await axios.post(`${BRIDGE_URL}/quotes`, {
                tokens: [
                    { instrument_token: ceStrike.pSymbol, exchange_segment: 'nse_fo' },
                    { instrument_token: peStrike.pSymbol, exchange_segment: 'nse_fo' }
                ]
            });
            const quotes = quotesRes.data.data.message || [];
            const ceQuote = quotes.find(q => q.instrument_token === ceStrike.pSymbol);
            const peQuote = quotes.find(q => q.instrument_token === peStrike.pSymbol);

            if (!ceQuote || !peQuote) return;

            const ceLtp = parseFloat(ceQuote.last_traded_price);
            const peLtp = parseFloat(peQuote.last_traded_price);

            // Calculate MTM
            const mtm = ((ceEntry - ceLtp) + (peEntry - peLtp)) * quantity;
            entrySummary.mtm = mtm.toFixed(2);
            entrySummary.details.ceLtp = ceLtp;
            entrySummary.details.peLtp = peLtp;

            io.emit('entry-summary', entrySummary);
        } catch (error) {
            console.error('Polling error (MTM):', error.message);
        }
    }

    // Also poll NIFTY and SENSEX spot prices for the header
    try {
        const [niftyRes, sensexRes] = await Promise.all([
            axios.get(`${BRIDGE_URL}/spot`, { params: { symbol: 'NIFTY' } }).catch(e => {
                console.error('NIFTY Spot fetch failed:', e.message);
                return null;
            }),
            axios.get(`${BRIDGE_URL}/spot`, { params: { symbol: 'SENSEX' } }).catch(e => {
                console.error('SENSEX Spot fetch failed:', e.message);
                return null;
            })
        ]);

        if (niftyRes?.data?.quote?.message?.[0]) {
            spotPrices.NIFTY = parseFloat(niftyRes.data.quote.message[0].last_traded_price).toFixed(2);
        } else if (niftyRes?.data) {
            console.warn('NIFTY Spot response missing data:', niftyRes.data);
        }

        if (sensexRes?.data?.quote?.message?.[0]) {
            spotPrices.SENSEX = parseFloat(sensexRes.data.quote.message[0].last_traded_price).toFixed(2);
        } else if (sensexRes?.data) {
            console.warn('SENSEX Spot response missing data:', sensexRes.data);
        }

        io.emit('spot-prices', spotPrices);
    } catch (error) {
        console.error('Critical polling error (Spots):', error.message);
    }
}, 5000); // Every 5 seconds

app.post('/api/login', async (req, res) => {
    try {
        console.log(`Forwarding login request to bridge for UCC: ${req.body.ucc}`);
        const response = await axios.post(`${BRIDGE_URL}/login`, req.body);
        console.log(`Bridge login response:`, response.data);
        res.json(response.data);
    } catch (error) {
        console.error('Login error forwarding:', error.message);
        res.status(error.response?.status || 500).json(error.response?.data || { message: error.message });
    }
});

app.get('/api/instruments', async (req, res) => {
    try {
        const response = await axios.get(`${BRIDGE_URL}/instruments`, { params: req.query });
        res.json(response.data);
    } catch (error) {
        res.status(error.response?.status || 500).json(error.response?.data || { message: error.message });
    }
});

app.get('/api/strikes', async (req, res) => {
    try {
        const response = await axios.get(`${BRIDGE_URL}/strikes`, { params: req.query });
        res.json(response.data);
    } catch (error) {
        res.status(error.response?.status || 500).json(error.response?.data || { message: error.message });
    }
});

app.get('/api/spot', async (req, res) => {
    try {
        const response = await axios.get(`${BRIDGE_URL}/spot`, { params: req.query });
        res.json(response.data);
    } catch (error) {
        res.status(error.response?.status || 500).json(error.response?.data || { message: error.message });
    }
});

app.post('/api/execute-strategy', async (req, res) => {
    const { strategy, underlying, expiry, lots, targetPremium, stopLoss, percentageOTM } = req.body;
    try {
        let result;
        if (strategy === 'Short Straddle') {
            result = await strategies.executeShortStraddle(BRIDGE_URL, { underlying, expiry, lots, stopLoss });
        } else if (strategy === 'Premium Based') {
            result = await strategies.executePremiumBasedStrangle(BRIDGE_URL, { underlying, expiry, lots, targetPremium, stopLoss });
        } else if (strategy === 'Spot Based Strangle') {
            result = await strategies.executeSpotBasedStrangle(BRIDGE_URL, { underlying, expiry, lots, percentageOTM, stopLoss });
        }
        entrySummary = { strategy, underlying, expiry, lots, status: 'Executed', details: result, timestamp: new Date().toISOString() };
        io.emit('entry-summary', entrySummary);
        res.json({ status: 'success', data: result });
    } catch (error) {
        console.error('Strategy Execution Error:', error);
        res.status(500).json({
            status: 'error',
            message: error.message,
            stack: process.env.NODE_ENV === 'development' ? error.stack : undefined
        });
    }
});

app.post('/api/schedule-job', (req, res) => {
    const { name, time, config } = req.body;
    const job = { id: Date.now(), name, time, config, status: 'Queued' };
    scheduledJobs.push(job);
    const [hour, minute] = time.split(':');

    schedule.scheduleJob(`${minute} ${hour} * * *`, async () => {
        console.log(`Running scheduled job: ${name}`);
        job.status = 'Running';
        io.emit('scheduled-jobs', scheduledJobs);
        try {
            const { strategy, underlying, expiry, lots, targetPremium, stopLoss, percentageOTM } = config;
            let result;
            if (strategy === 'Short Straddle') {
                result = await strategies.executeShortStraddle(BRIDGE_URL, { underlying, expiry, lots, stopLoss });
            } else if (strategy === 'Premium Based') {
                result = await strategies.executePremiumBasedStrangle(BRIDGE_URL, { underlying, expiry, lots, targetPremium, stopLoss });
            } else if (strategy === 'Spot Based Strangle') {
                result = await strategies.executeSpotBasedStrangle(BRIDGE_URL, { underlying, expiry, lots, percentageOTM, stopLoss });
            }
            job.status = 'Completed';
            entrySummary = { strategy, underlying, expiry, lots, status: 'Executed (Scheduled)', details: result, timestamp: new Date().toISOString() };
            io.emit('entry-summary', entrySummary);
        } catch (error) {
            console.error(`Scheduled job ${name} failed:`, error.message);
            job.status = 'Failed';
        }
        io.emit('scheduled-jobs', scheduledJobs);
    });

    io.emit('scheduled-jobs', scheduledJobs);
    res.json({ status: 'success', job });
});

app.get('/api/scheduled-jobs', (req, res) => res.json(scheduledJobs));
app.get('/api/entry-summary', (req, res) => res.json(entrySummary));

io.on('connection', (socket) => {
    console.log('New client connected');
    socket.emit('scheduled-jobs', scheduledJobs);
    socket.emit('entry-summary', entrySummary);
    socket.emit('spot-prices', spotPrices);
});

const PORT = process.env.PORT || 5000;
server.listen(PORT, () => console.log(`Server running on port ${PORT}`));
