import React, { useState, useEffect } from 'react';
import Login from './components/Login';
import Dashboard from './components/Dashboard';
import { io } from 'socket.io-client';

const socket = io('http://localhost:5000');

function App() {
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [scheduledJobs, setScheduledJobs] = useState([]);
  const [entrySummary, setEntrySummary] = useState(null);

  useEffect(() => {
    socket.on('scheduled-jobs', (jobs) => {
      setScheduledJobs(jobs);
    });

    socket.on('entry-summary', (summary) => {
      setEntrySummary(summary);
    });

    return () => {
      socket.off('scheduled-jobs');
      socket.off('entry-summary');
    };
  }, []);

  if (!isLoggedIn) {
    return <Login onLoginSuccess={() => setIsLoggedIn(true)} />;
  }

  return (
    <div className="min-h-screen bg-black text-white">
      <Dashboard
        scheduledJobs={scheduledJobs}
        entrySummary={entrySummary}
        setScheduledJobs={setScheduledJobs}
      />
    </div>
  );
}

export default App;
