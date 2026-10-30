import React, { useState, useEffect } from 'react';
import { Job, JobPaymentRecord } from '../../types';
import { useAuth } from '../../context/AuthContext';
import { useApp } from '../../context/AppContext';
import { api } from '../../services/api/apiClient';
import {
  openRazorpayStandardCheckout,
  loadRazorpayCheckoutScript,
} from '../../services/payment/razorpayCheckout';
import {
  CreditCard,
  ShieldCheck,
  CheckCircle2,
  FileCheck2,
  Printer,
  AlertTriangle,
  Receipt,
  Lock,
  Zap,
  Sparkles,
  RefreshCw,
} from 'lucide-react';

interface PaymentCheckoutPanelProps {
  job: Job;
  onPaymentSuccess?: () => void;
}

export const PaymentCheckoutPanel: React.FC<PaymentCheckoutPanelProps> = ({
  job,
  onPaymentSuccess,
}) => {
  const { user } = useAuth();
  const { refreshData } = useApp();

  const [isProcessing, setIsProcessing] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');
  const [successMsg, setSuccessMsg] = useState('');
  const [backendConfig, setBackendConfig] = useState<{
    configured: boolean;
    keyId: string | null;
  }>({
    configured: false,
    keyId: null,
  });

  // Electrical pricing breakdown
  const serviceCharge = 399; // Diagnostic & Inspection Fee
  const partsCharge = 550; // Materials & Replacements
  const subtotal = serviceCharge + partsCharge; // 949
  const taxAmount = Math.round(subtotal * 0.18); // 171 (18% GST)
  const totalAmountInr = subtotal + taxAmount; // 1,120
  const amountPaise = totalAmountInr * 100;

  // Check if backend or environment has Razorpay Test Key
  useEffect(() => {
    fetch('http://localhost:8000/api/v1/payments/config')
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => {
        if (data && data.razorpay_configured) {
          setBackendConfig({ configured: true, keyId: data.razorpay_key_id });
        }
      })
      .catch(() => {
        // Fallback: mock test mode active
      });
  }, []);

  // 1. Live Razorpay Test Mode Checkout
  const handleRazorpayTestCheckout = async () => {
    if (!user) return;
    setErrorMsg('');
    setSuccessMsg('');
    setIsProcessing(true);

    try {
      const keyId =
        backendConfig.keyId ||
        import.meta.env.VITE_RAZORPAY_KEY_ID ||
        'rzp_test_placeholder_key';

      // Check if SDK can load
      const sdkReady = await loadRazorpayCheckoutScript();
      if (!sdkReady || !window.Razorpay) {
        throw new Error(
          'Razorpay checkout script could not be loaded from checkout.razorpay.com. Use the Instant Demo Payment option below.'
        );
      }

      const mockOrderId = `order_${Date.now().toString(36)}`;
      const paymentCode = `PAY-${Math.random().toString(36).substr(2, 6).toUpperCase()}`;

      await openRazorpayStandardCheckout(
        {
          razorpay_key_id: keyId,
          amount_paise: amountPaise,
          currency: 'INR',
          razorpay_order_id: mockOrderId,
          booking_code: job.id,
          payment_code: paymentCode,
          customer_name: user.name,
          customer_email: user.email,
          customer_phone: user.phone,
        },
        {
          onSuccess: async (payload) => {
            await finalizePayment({
              paymentId: payload.razorpay_payment_id || `pay_test_${Date.now().toString(36)}`,
              orderId: payload.razorpay_order_id || mockOrderId,
              razorpaySignature: payload.razorpay_signature,
              method: 'razorpay_test_mode',
            });
          },
          onDismiss: () => {
            setIsProcessing(false);
            setErrorMsg('Razorpay payment modal closed without completing checkout.');
          },
          onFailed: (reason) => {
            setIsProcessing(false);
            setErrorMsg(`Payment declined: ${reason}`);
          },
        }
      );
    } catch (err: any) {
      console.warn('Razorpay SDK error, prompting simulated payment:', err);
      setErrorMsg(err.message || 'Razorpay checkout encountered an issue. You can use the instant sandbox button.');
      setIsProcessing(false);
    }
  };

  // 2. Simulated Instant Payment (Test Sandbox Fallback)
  const handleSimulateInstantPayment = async () => {
    if (!user) return;
    setErrorMsg('');
    setIsProcessing(true);

    // Simulate 600ms network settlement
    await new Promise((r) => setTimeout(r, 600));

    const testPaymentId = `pay_test_${Math.random().toString(36).substring(2, 10)}${Date.now().toString(36)}`;
    const testOrderId = `order_test_${Math.random().toString(36).substring(2, 8)}`;

    await finalizePayment({
      paymentId: testPaymentId,
      orderId: testOrderId,
      method: 'razorpay_instant_sandbox',
    });
  };

  const finalizePayment = async (details: {
    paymentId: string;
    orderId: string;
    razorpaySignature?: string;
    method: string;
  }) => {
    if (!user) return;
    try {
      const paymentRecord: JobPaymentRecord = {
        paymentId: details.paymentId,
        orderId: details.orderId,
        amountPaise,
        amountInr: totalAmountInr,
        currency: 'INR',
        status: 'completed',
        razorpayPaymentId: details.paymentId,
        razorpayOrderId: details.orderId,
        razorpaySignature: details.razorpaySignature,
        paidAt: new Date().toISOString(),
        method: details.method,
        serviceCharge,
        partsCharge,
        taxAmount,
        receiptNumber: `REC-MYS-${Date.now().toString().slice(-6)}`,
      };

      await api.updateJobPayment(job.id, paymentRecord, user);
      refreshData();
      setSuccessMsg('Payment successfully verified and recorded! Job marked as Customer Confirmed.');
      if (onPaymentSuccess) onPaymentSuccess();
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to record payment in ElectroGrid.');
    } finally {
      setIsProcessing(false);
    }
  };

  // RENDER ALREADY COMPLETED RECEIPT
  if (job.payment && job.payment.status === 'completed') {
    const p = job.payment;
    return (
      <div className="bg-gradient-to-br from-emerald-50/80 via-white to-emerald-50/30 rounded-2xl p-5 sm:p-6 border-2 border-emerald-300 shadow-sm space-y-4">
        {/* Receipt Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-emerald-200">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-emerald-600 text-white flex items-center justify-center flex-shrink-0 shadow-sm">
              <CheckCircle2 className="w-6 h-6" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-xs font-extrabold uppercase tracking-wider text-emerald-800">
                  Payment Settled & Confirmed
                </span>
                <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-100 text-emerald-800 border border-emerald-200">
                  Razorpay Test Mode
                </span>
              </div>
              <h4 className="text-base font-extrabold text-slate-900 mt-0.5">
                Receipt #{p.receiptNumber || 'REC-MYS-882104'}
              </h4>
            </div>
          </div>

          <button
            type="button"
            onClick={() => window.print()}
            className="px-3.5 py-2 bg-white hover:bg-slate-50 border border-slate-200 rounded-xl text-xs font-bold text-slate-700 flex items-center gap-1.5 shadow-xs transition cursor-pointer self-start sm:self-auto"
          >
            <Printer className="w-4 h-4 text-slate-500" />
            Print / Save Receipt
          </button>
        </div>

        {/* Itemized Table */}
        <div className="text-xs space-y-2 bg-white/80 p-3.5 rounded-xl border border-emerald-100">
          <div className="flex justify-between text-slate-600">
            <span>Electrical Diagnostic & Field Inspection Fee:</span>
            <span className="font-semibold text-slate-800">₹{p.serviceCharge || serviceCharge}</span>
          </div>
          <div className="flex justify-between text-slate-600">
            <span>Spare Parts & Replacement Consumables:</span>
            <span className="font-semibold text-slate-800">₹{p.partsCharge || partsCharge}</span>
          </div>
          <div className="flex justify-between text-slate-600">
            <span>GST (18% Goods & Services Tax):</span>
            <span className="font-semibold text-slate-800">₹{p.taxAmount || taxAmount}</span>
          </div>
          <div className="pt-2 border-t border-slate-200 flex justify-between text-sm font-extrabold text-slate-900">
            <span>Total Paid (INR):</span>
            <span className="text-emerald-700 font-mono text-base">
              ₹{p.amountInr.toLocaleString('en-IN')}
            </span>
          </div>
        </div>

        {/* Audit Meta */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-[11px] text-slate-500 pt-1">
          <div>
            <span className="font-semibold text-slate-700">Razorpay Payment ID: </span>
            <code className="text-blue-700 font-mono font-bold bg-blue-50 px-1 rounded">
              {p.razorpayPaymentId || p.paymentId}
            </code>
          </div>
          <div>
            <span className="font-semibold text-slate-700">Settled At: </span>
            <span>{p.paidAt ? new Date(p.paidAt).toLocaleString('en-IN') : 'Just now'}</span>
          </div>
        </div>
      </div>
    );
  }

  // RENDER PAYMENT CHECKOUT FORM
  return (
    <div className="bg-white rounded-2xl p-5 sm:p-6 border-2 border-blue-200 shadow-md space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between pb-3 border-b border-slate-100">
        <div className="flex items-center gap-2.5">
          <div className="w-9 h-9 rounded-xl bg-blue-600 text-white flex items-center justify-center shadow-sm">
            <CreditCard className="w-5 h-5" />
          </div>
          <div>
            <h4 className="text-sm font-extrabold text-slate-900">
              Customer Payment Checkout
            </h4>
            <p className="text-xs text-slate-500">
              Review technician completion proof & settle electrical service charges
            </p>
          </div>
        </div>

        <span className="px-2.5 py-1 rounded-full text-[11px] font-bold bg-amber-50 text-amber-800 border border-amber-200">
          Payment Due
        </span>
      </div>

      {errorMsg && (
        <div className="p-3 bg-red-50 border border-red-200 text-red-700 text-xs rounded-xl flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 flex-shrink-0" />
          <span>{errorMsg}</span>
        </div>
      )}

      {successMsg && (
        <div className="p-3 bg-emerald-50 border border-emerald-200 text-emerald-700 text-xs rounded-xl flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 flex-shrink-0" />
          <span>{successMsg}</span>
        </div>
      )}

      {/* Transparent Price Summary */}
      <div className="bg-slate-50 p-4 rounded-xl border border-slate-200 text-xs space-y-2">
        <div className="flex justify-between text-slate-600">
          <span>Certified Electrician Inspection & Labour:</span>
          <span className="font-semibold text-slate-800">₹{serviceCharge}</span>
        </div>
        <div className="flex justify-between text-slate-600">
          <span>Parts & Consumables (Circuit Breakers / Cable Fault Repair):</span>
          <span className="font-semibold text-slate-800">₹{partsCharge}</span>
        </div>
        <div className="flex justify-between text-slate-600">
          <span>Applicable GST (CGST 9% + SGST 9%):</span>
          <span className="font-semibold text-slate-800">₹{taxAmount}</span>
        </div>
        <div className="pt-2 border-t border-slate-200 flex justify-between text-sm font-extrabold text-slate-900">
          <span>Total Payable Amount:</span>
          <span className="text-blue-700 font-mono text-base">₹{totalAmountInr.toLocaleString('en-IN')}</span>
        </div>
      </div>

      {/* Technician Sign-Off Verification Proof Note */}
      {job.completionReport && (
        <div className="p-3 bg-blue-50/60 border border-blue-200 rounded-xl text-xs space-y-1">
          <div className="flex items-center gap-1.5 text-blue-900 font-bold">
            <FileCheck2 className="w-4 h-4 text-blue-600" />
            <span>Technician Sign-Off Verified</span>
          </div>
          <p className="text-slate-600">
            Work completed by <b>{job.completionReport.signedOffByElectrician}</b>: "{job.completionReport.workPerformed}".
          </p>
        </div>
      )}

      {/* Action Buttons */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-1">
        <button
          type="button"
          disabled={isProcessing}
          onClick={handleRazorpayTestCheckout}
          className="py-3 px-4 bg-blue-600 hover:bg-blue-700 text-white rounded-xl text-xs font-bold shadow-md shadow-blue-500/20 flex items-center justify-center gap-2 transition cursor-pointer disabled:opacity-60"
        >
          {isProcessing ? (
            <RefreshCw className="w-4 h-4 animate-spin" />
          ) : (
            <ShieldCheck className="w-4 h-4" />
          )}
          Pay ₹{totalAmountInr} via Razorpay (Test Mode)
        </button>

        <button
          type="button"
          disabled={isProcessing}
          onClick={handleSimulateInstantPayment}
          className="py-3 px-4 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-xs font-bold shadow-md shadow-emerald-500/20 flex items-center justify-center gap-2 transition cursor-pointer disabled:opacity-60"
        >
          <Sparkles className="w-4 h-4" />
          Simulate Instant Test Payment (Offline Sandbox)
        </button>
      </div>

      <div className="flex items-center justify-center gap-2 text-[11px] text-slate-400">
        <Lock className="w-3.5 h-3.5 text-slate-400" />
        <span>Secured via Razorpay Test Mode • 256-Bit SSL Encryption • No real money debited</span>
      </div>
    </div>
  );
};

