import React, { useState, useEffect } from 'react';
import Login from './components/Login';
import Dashboard from './components/Dashboard';
import { io } from 'socket.io-client';

const socket = io('http://localhost:5000');

function App() {
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [ucc, setUcc] = useState('');
  const [scheduledJobs, setScheduledJobs] = useState([]);
  const [entrySummary, setEntrySummary] = useState(null);
  const [spotPrices, setSpotPrices] = useState({ NIFTY: '0.00', SENSEX: '0.00' });

  useEffect(() => {
    socket.on('scheduled-jobs', (jobs) => {
      setScheduledJobs(jobs);
    });

    socket.on('entry-summary', (summary) => {
      setEntrySummary(summary);
    });

    socket.on('spot-prices', (prices) => {
      setSpotPrices(prices);
    });

    return () => {
      socket.off('scheduled-jobs');
      socket.off('entry-summary');
      socket.off('spot-prices');
    };
  }, []);

  if (!isLoggedIn) {
    return <Login onLoginSuccess={(userUcc) => {
      setUcc(userUcc);
      setIsLoggedIn(true);
    }} />;
  }

  return (
    <div className="min-h-screen bg-black text-white">
      <Dashboard
        scheduledJobs={scheduledJobs}
        entrySummary={entrySummary}
        setScheduledJobs={setScheduledJobs}
        ucc={ucc}
        spotPrices={spotPrices}
      />
    </div>
  );
}

export default App;
