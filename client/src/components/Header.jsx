import React from 'react';
import { User, Activity } from 'lucide-react';

const Header = ({ ucc, spotPrices }) => {
  return (
    <div className="flex flex-col md:flex-row items-center justify-between bg-dark-panel border border-dark-border p-4 rounded-xl shadow-lg">
      <div className="flex items-center gap-3 mb-4 md:mb-0">
        <div className="p-2 bg-primary/10 rounded-lg">
          <User size={20} className="text-primary" />
        </div>
        <div>
          <h1 className="text-lg font-bold">Welcome, <span className="text-primary">{ucc || 'User'}</span></h1>
          <p className="text-[10px] text-gray-500 uppercase tracking-widest font-bold">Trading Dashboard Active</p>
        </div>
      </div>

      <div className="flex items-center gap-6">
        <div className="flex items-center gap-3 px-4 py-2 bg-dark-card/50 border border-dark-border rounded-lg">
          <Activity size={16} className={spotPrices.NIFTY === '0.00' ? "text-gray-600 animate-pulse" : "text-green-500"} />
          <div>
            <div className="text-[8px] text-gray-500 uppercase font-bold">NIFTY 50</div>
            <div className={`text-sm font-mono font-bold tracking-tight ${spotPrices.NIFTY === '0.00' ? 'text-gray-600' : ''}`}>
              {spotPrices.NIFTY === '0.00' ? 'Loading...' : `₹${spotPrices.NIFTY}`}
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3 px-4 py-2 bg-dark-card/50 border border-dark-border rounded-lg">
          <Activity size={16} className={spotPrices.SENSEX === '0.00' ? "text-gray-600 animate-pulse" : "text-primary"} />
          <div>
            <div className="text-[8px] text-gray-500 uppercase font-bold">SENSEX</div>
            <div className={`text-sm font-mono font-bold tracking-tight ${spotPrices.SENSEX === '0.00' ? 'text-gray-600' : ''}`}>
              {spotPrices.SENSEX === '0.00' ? 'Loading...' : `₹${spotPrices.SENSEX}`}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Header;
