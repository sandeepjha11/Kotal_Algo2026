import React from 'react';
import ScheduledJobs from './ScheduledJobs';
import OrderConfig from './OrderConfig';
import EntrySummary from './EntrySummary';
import Header from './Header';
const Dashboard = ({ scheduledJobs, entrySummary, setScheduledJobs, ucc, spotPrices }) => {
  return (
    <div className="p-6 space-y-6">
      <Header ucc={ucc} spotPrices={spotPrices} />
      <div className="grid grid-cols-1 md:grid-cols-12 gap-6">
        <div className="md:col-span-3 bg-dark-panel border border-dark-border rounded-xl p-5 min-h-[80vh]">
          <h2 className="text-xl font-bold flex items-center mb-6"><span className="text-primary mr-2">🕒</span> Scheduled Jobs</h2>
          <ScheduledJobs jobs={scheduledJobs} setJobs={setScheduledJobs} />
        </div>
        <div className="md:col-span-4 bg-dark-panel border border-dark-border rounded-xl p-5 min-h-[80vh]">
          <h2 className="text-xl font-bold flex items-center mb-6"><span className="text-primary mr-2">●</span> Order Configuration</h2>
          <OrderConfig />
        </div>
        <div className="md:col-span-5 bg-dark-panel border border-dark-border rounded-xl p-5 min-h-[80vh]">
          <h2 className="text-xl font-bold flex items-center mb-6"><span className="text-green-500 mr-2">●</span> Entry Summary</h2>
          <EntrySummary summary={entrySummary} />
        </div>
      </div>
    </div>
  );
};
export default Dashboard;
