import React from 'react';
const EntrySummary = ({ summary }) => {
  if (!summary) return <div className="flex flex-col items-center justify-center h-full text-gray-600 italic"><p>No active entry summary</p></div>;
  const { strategy, underlying, expiry, status, details, timestamp } = summary;
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-4 gap-3">
        <div className="bg-dark-card border border-dark-border p-3 rounded-xl text-center"><div className="text-[8px] text-gray-500 uppercase font-bold mb-1">Expiry</div><div className="text-primary font-bold text-sm leading-tight">{expiry}</div></div>
        <div className="bg-dark-card border border-dark-border p-3 rounded-xl text-center"><div className="text-[8px] text-gray-500 uppercase font-bold mb-1">Spot Price</div><div className="text-gray-200 font-bold text-sm leading-tight">₹{details?.spotPrice || '-'}</div></div>
        <div className="bg-dark-card border border-dark-border p-3 rounded-xl text-center"><div className="text-[8px] text-gray-500 uppercase font-bold mb-1">CE Strike</div><div className="text-gray-200 font-bold text-sm leading-tight">{details?.ceStrike?.pStrikePrice || '-'}</div></div>
        <div className="bg-dark-card border border-dark-border p-3 rounded-xl text-center"><div className="text-[8px] text-gray-500 uppercase font-bold mb-1">PE Strike</div><div className="text-gray-200 font-bold text-sm leading-tight">{details?.peStrike?.pStrikePrice || '-'}</div></div>
        <div className="bg-dark-card border border-dark-border p-3 rounded-xl text-center"><div className="text-[8px] text-gray-500 uppercase font-bold mb-1">Unrealized P&L (MTM)</div><div className={`${summary.mtm >= 0 ? 'text-green-500' : 'text-red-500'} font-bold text-sm leading-tight`}>₹{summary.mtm || '0.00'}</div></div>
      </div>
      <div className="overflow-x-auto"><table className="w-full text-[10px]"><thead><tr className="text-gray-500 uppercase tracking-wider border-b border-dark-border"><th className="text-left pb-3 font-medium">Symbol</th><th className="text-left pb-3 font-medium">Type</th><th className="text-left pb-3 font-medium">Strike</th><th className="text-left pb-3 font-medium">Qty</th><th className="text-left pb-3 font-medium">Entry</th><th className="text-right pb-3 font-medium">SL Trigger</th></tr></thead>
          <tbody className="divide-y divide-dark-border/50">
            {[
              { type: 'CE', strike: details?.ceStrike?.pStrikePrice, qty: details?.quantity, entry: details?.ceEntry, sl: details?.ceSL },
              { type: 'PE', strike: details?.peStrike?.pStrikePrice, qty: details?.quantity, entry: details?.peEntry, sl: details?.peSL }
            ].map((row, idx) => (
              <tr key={idx} className="hover:bg-dark-card/30 transition-colors"><td className="py-4"><div>{underlying}</div><div className="text-gray-500">{row.strike} {row.type}</div></td><td><span className={`px-2 py-0.5 rounded-full ${row.type === 'CE' ? 'bg-green-900/20 text-green-500 border border-green-500/30' : 'bg-red-900/20 text-red-500 border border-red-500/30'}`}>{row.type}</span></td><td>{row.strike}</td><td>{row.qty}</td><td className="text-primary font-bold">₹{row.entry}</td><td className="text-right text-red-500 font-bold">₹{row.sl}</td></tr>
            ))}
          </tbody></table></div>
      <div className="w-full h-1.5 bg-dark-card rounded-full overflow-hidden"><div className="bg-primary h-full w-[65%]" /></div>
    </div>
  );
};
export default EntrySummary;
