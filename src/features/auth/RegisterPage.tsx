import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { CustomerCategory } from '../../types';
import { MYSURU_LOCALITIES } from '../../data/seedData';
import {
  Zap,
  Building,
  User,
  CheckCircle2,
  Lock,
  Eye,
  EyeOff,
  MapPin,
  Mail,
  Phone,
  AlertCircle,
} from 'lucide-react';

export const RegisterPage: React.FC = () => {
  const { registerCustomer } = useAuth();
  const navigate = useNavigate();

  const [category, setCategory] = useState<CustomerCategory>('individual');
  const [name, setName] = useState('');
  const [companyName, setCompanyName] = useState('');
  const [email, setEmail] = useState('');
  const [phone, setPhone] = useState('');
  const [locality, setLocality] = useState(MYSURU_LOCALITIES[0].name);
  const [address, setAddress] = useState('');
  const [city, setCity] = useState('Mysuru');
  const [postalCode, setPostalCode] = useState('570009');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    // Field Validations
    if (!name.trim()) {
      setError('Full name is required.');
      return;
    }

    if (category === 'commercial' && !companyName.trim()) {
      setError('Company / Organization name is required for commercial registration.');
      return;
    }

    if (!email.trim() || !email.includes('@')) {
      setError('Please provide a valid email address.');
      return;
    }

    if (!phone.trim()) {
      setError('Contact phone number is required.');
      return;
    }

    if (!address.trim()) {
      setError('Primary service address is required.');
      return;
    }

    if (!password || password.length < 6) {
      setError('Password must be at least 6 characters long.');
      return;
    }

    if (password !== confirmPassword) {
      setError('Passwords do not match. Please re-enter confirm password.');
      return;
    }

    setIsLoading(true);

    try {
      const fullAddress = `${address.trim()}, ${locality}`;
      await registerCustomer({
        name: name.trim(),
        email: email.trim().toLowerCase(),
        phone: phone.trim(),
        password: password.trim(),
        customerCategory: category,
        companyName: category === 'commercial' ? companyName.trim() : undefined,
        address: fullAddress,
        city: city.trim() || 'Mysuru',
        postalCode: postalCode.trim() || '570009',
      });

      navigate('/customer/dashboard');
    } catch (err: any) {
      setError(err.message || 'Failed to register account.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-100 flex flex-col justify-center py-10 px-4 sm:px-6 lg:px-8">
      <div className="sm:mx-auto sm:w-full sm:max-w-lg text-center mb-6">
        <div className="mx-auto w-12 h-12 rounded-2xl bg-gradient-to-tr from-blue-600 to-indigo-600 flex items-center justify-center text-white shadow-lg shadow-blue-500/30">
          <Zap className="w-7 h-7 fill-white text-white" />
        </div>
        <h2 className="mt-4 text-2xl font-extrabold text-slate-900 tracking-tight">
          Create Customer Account
        </h2>
        <p className="mt-1 text-sm text-slate-500">
          Register to dispatch certified Mysuru electricians and manage power infrastructure
        </p>
      </div>

      <div className="sm:mx-auto sm:w-full sm:max-w-xl">
        <div className="bg-white py-8 px-6 shadow-xl rounded-2xl sm:px-10 border border-slate-200">
          {/* Customer Category Toggle */}
          <div className="grid grid-cols-2 gap-3 mb-6 p-1 bg-slate-100 rounded-xl">
            <button
              type="button"
              onClick={() => setCategory('individual')}
              className={`flex items-center justify-center gap-2 py-2.5 rounded-lg text-xs font-bold transition cursor-pointer ${
                category === 'individual'
                  ? 'bg-white text-blue-600 shadow-sm'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              <User className="w-4 h-4" />
              Individual Customer
            </button>
            <button
              type="button"
              onClick={() => setCategory('commercial')}
              className={`flex items-center justify-center gap-2 py-2.5 rounded-lg text-xs font-bold transition cursor-pointer ${
                category === 'commercial'
                  ? 'bg-white text-blue-600 shadow-sm'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              <Building className="w-4 h-4" />
              Commercial Enterprise
            </button>
          </div>

          {error && (
            <div className="mb-4 p-3 rounded-xl bg-red-50 border border-red-200 text-xs text-red-700 flex items-start gap-2">
              <AlertCircle className="w-4 h-4 text-red-600 flex-shrink-0 mt-0.5" />
              <span>{error}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            {category === 'commercial' ? (
              <>
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Company / Organization Name *
                  </label>
                  <input
                    type="text"
                    required
                    value={companyName}
                    onChange={(e) => setCompanyName(e.target.value)}
                    placeholder="e.g. Mysore Silk Emporium Pvt Ltd"
                    className="w-full px-3.5 py-2 text-sm rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-600"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Authorized Contact Person *
                  </label>
                  <input
                    type="text"
                    required
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="e.g. Suresh Nagaraj"
                    className="w-full px-3.5 py-2 text-sm rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-600"
                  />
                </div>
              </>
            ) : (
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Full Name *
                </label>
                <input
                  type="text"
                  required
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="e.g. Ananya Rao"
                  className="w-full px-3.5 py-2 text-sm rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-600"
                />
              </div>
            )}

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Email Address *
                </label>
                <div className="relative">
                  <input
                    type="email"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder={category === 'commercial' ? 'facilities@company.in' : 'ananya@example.com'}
                    className="w-full pl-9 pr-3.5 py-2 text-sm rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-600"
                  />
                  <Mail className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
                </div>
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Contact Phone *
                </label>
                <div className="relative">
                  <input
                    type="tel"
                    required
                    value={phone}
                    onChange={(e) => setPhone(e.target.value)}
                    placeholder="+91 98450 21001"
                    className="w-full pl-9 pr-3.5 py-2 text-sm rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-600"
                  />
                  <Phone className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
                </div>
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Mysuru Locality / Distribution Area *
              </label>
              <select
                value={locality}
                onChange={(e) => setLocality(e.target.value)}
                className="w-full px-3.5 py-2 text-sm rounded-lg border border-slate-200 bg-white focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-600"
              >
                {MYSURU_LOCALITIES.map((loc) => (
                  <option key={loc.name} value={loc.name}>
                    {loc.name} (CHESCOM Feeder: {loc.name} Grid)
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Primary Service Address *
              </label>
              <div className="relative">
                <input
                  type="text"
                  required
                  value={address}
                  onChange={(e) => setAddress(e.target.value)}
                  placeholder="e.g. #142, 5th Cross, Near Railway Workshop"
                  className="w-full pl-9 pr-3.5 py-2 text-sm rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-600"
                />
                <MapPin className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">City</label>
                <input
                  type="text"
                  required
                  value={city}
                  onChange={(e) => setCity(e.target.value)}
                  className="w-full px-3.5 py-2 text-sm rounded-lg border border-slate-200 bg-slate-50 text-slate-700"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Postal Code</label>
                <input
                  type="text"
                  required
                  value={postalCode}
                  onChange={(e) => setPostalCode(e.target.value)}
                  className="w-full px-3.5 py-2 text-sm rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-600"
                />
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-1">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Password (min. 6 characters) *
                </label>
                <div className="relative">
                  <input
                    type={showPassword ? 'text' : 'password'}
                    required
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="Create secure password"
                    className="w-full pl-9 pr-10 py-2 text-sm rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-600"
                  />
                  <Lock className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3 top-2.5 text-slate-400 hover:text-slate-600"
                  >
                    {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Confirm Password *
                </label>
                <div className="relative">
                  <input
                    type={showPassword ? 'text' : 'password'}
                    required
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    placeholder="Re-enter password"
                    className="w-full pl-9 pr-3.5 py-2 text-sm rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-600"
                  />
                  <Lock className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
                </div>
              </div>
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="w-full mt-4 py-2.5 px-4 rounded-xl text-sm font-bold text-white bg-blue-600 hover:bg-blue-700 shadow-md shadow-blue-500/20 transition flex items-center justify-center gap-2 cursor-pointer disabled:opacity-60"
            >
              {isLoading ? 'Creating Customer Profile...' : 'Complete Registration'}
              <CheckCircle2 className="w-4 h-4" />
            </button>
          </form>

          <div className="mt-6 text-center text-xs text-slate-500">
            Already registered?{' '}
            <Link to="/login" className="font-semibold text-blue-600 hover:underline">
              Sign In with Credentials
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
};
