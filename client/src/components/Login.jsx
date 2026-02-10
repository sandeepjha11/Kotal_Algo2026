import React, { useState } from 'react';
import axios from 'axios';
const Login = ({ onLoginSuccess }) => {
  const [formData, setFormData] = useState({ consumer_key: '', mobile_number: '', ucc: '', mpin: '', totp_key: '' });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const handleChange = (e) => setFormData({ ...formData, [e.target.name]: e.target.value });
  const handleSubmit = async (e) => {
    e.preventDefault(); setLoading(true); setError('');
    try {
      const response = await axios.post('http://localhost:5000/api/login', formData);
      if (response.data.status === 'success') {
        onLoginSuccess(response.data.ucc);
      } else {
        setError(response.data.message);
      }
    } catch (err) { setError(err.response?.data?.message || 'Login failed'); }
    finally { setLoading(false); }
  };
  return (
    <div className="flex items-center justify-center min-h-screen bg-black">
      <div className="w-full max-w-md p-8 bg-dark-panel border border-dark-border rounded-lg shadow-xl">
        <h2 className="text-3xl font-bold text-center text-primary mb-8">Kotak Neo Login</h2>
        {error && <div className="p-3 mb-6 bg-red-900/30 border border-red-500 text-red-500 rounded">{error}</div>}
        <form onSubmit={handleSubmit} className="space-y-6">
          {['consumer_key', 'mobile_number', 'ucc'].map(f => (
            <div key={f}><label className="block text-sm font-medium mb-1 uppercase tracking-tight text-gray-400 text-[10px]">{f.replace('_', ' ')}</label>
            <input type="text" name={f} value={formData[f]} onChange={handleChange} className="w-full p-3 bg-dark-card border border-dark-border rounded focus:border-primary outline-none" required /></div>
          ))}
          <div><label className="block text-sm font-medium mb-1 uppercase tracking-tight text-gray-400 text-[10px]">MPIN</label>
          <input type="password" name="mpin" value={formData.mpin} onChange={handleChange} className="w-full p-3 bg-dark-card border border-dark-border rounded focus:border-primary outline-none" required /></div>
          <div><label className="block text-sm font-medium mb-1 uppercase tracking-tight text-gray-400 text-[10px]">TOTP Key</label>
          <input type="text" name="totp_key" value={formData.totp_key} onChange={handleChange} className="w-full p-3 bg-dark-card border border-dark-border rounded focus:border-primary outline-none" required /></div>
          <button type="submit" disabled={loading} className="w-full p-3 bg-primary hover:bg-primary-hover text-black font-bold rounded transition duration-200 disabled:opacity-50">
            {loading ? 'Logging in...' : 'Login'}
          </button>
        </form>
      </div>
    </div>
  );
};
export default Login;
