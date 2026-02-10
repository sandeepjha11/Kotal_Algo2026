import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Target, Zap } from 'lucide-react';
const OrderConfig = () => {
  const [strategy, setStrategy] = useState('Premium Based');
  const [underlying, setUnderlying] = useState('SENSEX');
  const [targetPremium, setTargetPremium] = useState(50);
  const [percentageOTM, setPercentageOTM] = useState(1);
  const [lots, setLots] = useState(1);
  const [stopLoss, setStopLoss] = useState(20);
  const [expiries, setExpiries] = useState([]);
  const [selectedExpiry, setSelectedExpiry] = useState('');
  const [loading, setLoading] = useState(false);
  useEffect(() => { fetchExpiries(); }, [underlying]);
  const fetchExpiries = async () => {
    try {
      const response = await axios.get(`http://localhost:5000/api/instruments?symbol=${underlying}`);
      setExpiries(response.data.expiries);
      if (response.data.expiries.length > 0) setSelectedExpiry(response.data.expiries[0]);
    } catch (err) { console.error("Failed to fetch expiries"); }
  };
  const handleExecute = async () => {
    setLoading(true);
    try {
      await axios.post('http://localhost:5000/api/execute-strategy', { strategy, underlying, expiry: selectedExpiry, lots, targetPremium, percentageOTM, stopLoss });
      alert('Strategy execution started!');
    } catch (err) { alert('Execution failed: ' + (err.response?.data?.message || err.message)); }
    finally { setLoading(false); }
  };
  return (
    <div className="space-y-8">
      <div className="space-y-3"><label className="text-xs text-gray-400 uppercase tracking-wider font-bold flex items-center gap-2"><Target size={14} className="text-primary" /> Strategy</label>
        <div className="space-y-2">
          {['Short Straddle', 'Premium Based', 'Spot Based Strangle'].map((s) => (
            <div key={s} onClick={() => setStrategy(s)} className={`p-3 rounded-lg border cursor-pointer transition-all duration-200 ${strategy === s ? 'border-primary bg-primary/5' : 'border-dark-border bg-dark-card/50'}`}>
              <div className="flex items-center gap-3"><div className={`w-4 h-4 rounded-full border flex items-center justify-center ${strategy === s ? 'border-primary' : 'border-gray-600'}`}>{strategy === s && <div className="w-2 h-2 bg-primary rounded-full" />}</div>
                <div><div className="font-bold text-sm">{s}</div><div className="text-[10px] text-gray-500">{s === 'Short Straddle' && 'Sell ATM Call & Put at same strike'}{s === 'Premium Based' && 'Select strikes based on target premium'}{s === 'Spot Based Strangle' && 'Select OTM strikes at % from spot'}</div></div>
              </div>
            </div>
          ))}
        </div>
      </div>
      {strategy === 'Premium Based' && (
        <div className="space-y-2"><label className="text-xs text-gray-400 uppercase tracking-wider font-bold flex items-center gap-2"><Zap size={14} className="text-primary" /> Target Premium (₹)</label>
          <input type="number" value={targetPremium} onChange={(e) => setTargetPremium(e.target.value)} className="w-full p-3 bg-dark-card border border-dark-border rounded-lg outline-none focus:border-primary font-mono" />
        </div>
      )}
      {strategy === 'Spot Based Strangle' && (
        <div className="space-y-2"><label className="text-xs text-gray-400 uppercase tracking-wider font-bold flex items-center gap-2"><Zap size={14} className="text-primary" /> OTM Percentage (%)</label>
          <input type="number" step="0.1" value={percentageOTM} onChange={(e) => setPercentageOTM(e.target.value)} className="w-full p-3 bg-dark-card border border-dark-border rounded-lg outline-none focus:border-primary font-mono" />
        </div>
      )}
      <div className="space-y-2"><label className="text-xs text-gray-400 uppercase tracking-wider font-bold flex items-center gap-2"><Zap size={14} className="text-primary" /> Underlying Index</label>
        <select value={underlying} onChange={(e) => setUnderlying(e.target.value)} className="w-full p-3 bg-dark-card border border-dark-border rounded-lg outline-none focus:border-primary appearance-none cursor-pointer">
          <option value="NIFTY">NIFTY - NIFTY (Lot: 25)</option><option value="SENSEX">SENSEX - SENSEX (Lot: 10)</option>
        </select>
      </div>
      <div className="space-y-2"><label className="text-xs text-gray-400 uppercase tracking-wider font-bold">Expiry Date</label>
        <select value={selectedExpiry} onChange={(e) => setSelectedExpiry(e.target.value)} className="w-full p-3 bg-dark-card border border-dark-border rounded-lg outline-none focus:border-primary appearance-none cursor-pointer">
          {expiries.map(exp => <option key={exp} value={exp}>{exp}</option>)}
        </select>
      </div>
      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-2"><label className="text-xs text-gray-400 uppercase tracking-wider font-bold">Number of Lots</label><input type="number" value={lots} onChange={(e) => setLots(e.target.value)} className="w-full p-3 bg-dark-card border border-dark-border rounded-lg outline-none focus:border-primary font-mono" /></div>
        <div className="space-y-2"><label className="text-xs text-gray-400 uppercase tracking-wider font-bold">Stop Loss (%)</label><input type="number" value={stopLoss} onChange={(e) => setStopLoss(e.target.value)} className="w-full p-3 bg-dark-card border border-dark-border rounded-lg outline-none focus:border-primary font-mono" /></div>
      </div>
      <button onClick={handleExecute} disabled={loading} className="w-full py-4 bg-primary hover:bg-primary-hover text-black font-black uppercase tracking-widest rounded-lg transition-all transform active:scale-95 disabled:opacity-50">{loading ? 'Executing...' : 'Execute Strategy'}</button>
    </div>
  );
};
export default OrderConfig;
