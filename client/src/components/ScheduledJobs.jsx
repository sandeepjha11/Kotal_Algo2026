import React from 'react';
import { Trash2, CheckCircle } from 'lucide-react';
const ScheduledJobs = ({ jobs, setJobs }) => {
  const deleteJob = (id) => setJobs(jobs.filter(j => j.id !== id));
  return (
    <div className="space-y-4">
      {jobs.length === 0 && <p className="text-gray-500 text-center py-10">No jobs scheduled</p>}
      {jobs.map((job) => (
        <div key={job.id} className="bg-dark-card border border-dark-border p-4 rounded-lg relative">
          <div className="flex justify-between items-start mb-2">
            <div><h3 className="font-bold text-gray-200">{job.name}</h3><p className="text-xs text-gray-400">{job.time}</p></div>
            <span className={`text-[10px] px-2 py-0.5 rounded-full flex items-center gap-1 ${job.status === 'Executed' ? 'bg-green-900/30 text-green-500 border border-green-500' : 'bg-yellow-900/30 text-yellow-500 border border-yellow-500'}`}>
              {job.status === 'Executed' && <CheckCircle size={10} />}{job.status}
            </span>
          </div>
          <div className="grid grid-cols-2 gap-y-1 text-xs mt-3">
            <span className="text-gray-500">Spot:</span><span className="text-right text-gray-300 font-mono">₹{job.details?.spot || '-'}</span>
            <span className="text-gray-500">CE Strike:</span><span className="text-right text-green-500">{job.details?.ceStrike || '-'}</span>
            <span className="text-gray-500">PE Strike:</span><span className="text-right text-red-500">{job.details?.peStrike || '-'}</span>
            <span className="text-gray-500">Premium:</span><span className="text-right text-primary font-bold">₹{job.details?.premium || '-'}</span>
          </div>
          <button onClick={() => deleteJob(job.id)} className="mt-4 text-red-500 hover:text-red-400 p-1 rounded-md transition duration-200"><Trash2 size={16} /></button>
        </div>
      ))}
    </div>
  );
};
export default ScheduledJobs;
