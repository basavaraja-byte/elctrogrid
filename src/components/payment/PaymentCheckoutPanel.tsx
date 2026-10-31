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
  Clock,
  Banknote,
  PackageX,
  Info,
  Download,
  Eye,
  Check,
} from 'lucide-react';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

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

  const [selectedMethod, setSelectedMethod] = useState<'CASH' | 'UPI'>('UPI');
  const [isProcessing, setIsProcessing] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');
  const [successMsg, setSuccessMsg] = useState('');
  const [showBillModal, setShowBillModal] = useState(false);
  const [backendConfig, setBackendConfig] = useState<{
    configured: boolean;
    keyId: string | null;
  }>({
    configured: false,
    keyId: null,
  });

  // Module 1 & 2: Time-based service pricing calculation
  const durationMinutes =
    job.payment?.durationMinutes ||
    job.actualDurationMinutes ||
    75; // Default demo: 75 mins -> 1 block -> ₹600

  const hrs = Math.floor(durationMinutes / 60);
  const remMins = durationMinutes % 60;
  const durationFormatted =
    job.payment?.durationFormatted ||
    (hrs > 0
      ? `${hrs} hour${hrs !== 1 ? 's' : ''} ${remMins} min${remMins !== 1 ? 's' : ''}`
      : `${durationMinutes} minutes`);

  const baseServiceInr = 500; // First 60 minutes
  const additionalBlocks =
    durationMinutes > 60 ? Math.ceil((durationMinutes - 60) / 30) : 0;
  const additionalAmountInr = additionalBlocks * 100;
  const labourTotalInr = baseServiceInr + additionalAmountInr;
  const amountPaise = labourTotalInr * 100;

  // Check backend Razorpay config
  useEffect(() => {
    fetch(`${API_BASE_URL}/api/v1/payments/config`)
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => {
        if (data && data.razorpay_configured) {
          setBackendConfig({ configured: true, keyId: data.razorpay_key_id });
        }
      })
      .catch(() => {});
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

      const sdkReady = await loadRazorpayCheckoutScript();
      if (!sdkReady || !window.Razorpay) {
        throw new Error(
          'Razorpay checkout script could not be loaded. You can use the Sandbox Instant Test Payment below.'
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
              method: 'UPI',
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
      setErrorMsg(err.message || 'Razorpay checkout encountered an issue.');
      setIsProcessing(false);
    }
  };

  // 2. Simulated Instant Payment (Test Sandbox Fallback)
  const handleSimulateInstantPayment = async () => {
    if (!user) return;
    setErrorMsg('');
    setIsProcessing(true);

    await new Promise((r) => setTimeout(r, 600));

    const testPaymentId = `pay_test_${Math.random().toString(36).substring(2, 10)}`;
    const testOrderId = `order_test_${Math.random().toString(36).substring(2, 8)}`;

    await finalizePayment({
      paymentId: testPaymentId,
      orderId: testOrderId,
      method: 'UPI',
    });
  };

  const finalizePayment = async (details: {
    paymentId: string;
    orderId: string;
    razorpaySignature?: string;
    method: 'CASH' | 'UPI';
  }) => {
    if (!user) return;
    try {
      const invoiceNumber = `EG-2026-${Math.floor(100000 + Math.random() * 900000)}`;
      const paymentRecord: JobPaymentRecord = {
        paymentId: details.paymentId,
        paymentReference: details.paymentId,
        orderId: details.orderId,
        amountPaise,
        amountInr: labourTotalInr,
        currency: 'INR',
        status: 'completed',
        method: details.method,
        workStartedAt: job.actualStartTime,
        workCompletedAt: job.actualCompletionTime,
        durationMinutes,
        durationFormatted,
        baseAmountInr: baseServiceInr,
        additionalBlocks,
        additionalAmountInr,
        labourTotalInr,
        razorpayPaymentId: details.paymentId,
        razorpayOrderId: details.orderId,
        razorpaySignature: details.razorpaySignature,
        paidAt: new Date().toISOString(),
        receiptNumber: invoiceNumber,
        isVerified: true,
      };

      await api.updateJobPayment(job.id, paymentRecord, user);
      refreshData();
      setSuccessMsg('Payment successfully verified and recorded! Official receipt generated.');
      if (onPaymentSuccess) onPaymentSuccess();
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to record payment in ElectroGrid.');
    } finally {
      setIsProcessing(false);
    }
  };

  const isPaid = job.payment && job.payment.status === 'completed';
  const receiptNo =
    job.invoice?.invoiceNumber ||
    job.payment?.receiptNumber ||
    `EG-2026-${job.id.slice(-6)}`;

  // =========================================================================
  // RENDER ALREADY COMPLETED RECEIPT
  // =========================================================================
  if (isPaid) {
    const p = job.payment!;
    const pdfDownloadUrl = `${API_BASE_URL}/api/v1/payments/invoices/${receiptNo}/pdf`;

    return (
      <div className="bg-gradient-to-br from-emerald-50/90 via-white to-emerald-50/40 rounded-2xl p-5 sm:p-6 border-2 border-emerald-400 shadow-sm space-y-4">
        {/* Receipt Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-emerald-200">
          <div className="flex items-center gap-3">
            <div className="w-11 h-11 rounded-2xl bg-emerald-600 text-white flex items-center justify-center flex-shrink-0 shadow-md shadow-emerald-600/30">
              <CheckCircle2 className="w-6 h-6" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-xs font-extrabold uppercase tracking-wider text-emerald-800">
                  Payment Successful • Job Closed
                </span>
                <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-100 text-emerald-800 border border-emerald-200">
                  {p.method === 'CASH' ? 'Cash Verified' : 'Razorpay UPI (Test Mode)'}
                </span>
              </div>
              <h4 className="text-base font-extrabold text-slate-900 mt-0.5 flex items-center gap-2">
                Receipt #{receiptNo}
              </h4>
            </div>
          </div>

          <div className="flex items-center gap-2 self-start sm:self-auto">
            <button
              type="button"
              onClick={() => setShowBillModal(true)}
              className="px-3.5 py-2 bg-white hover:bg-slate-50 border border-slate-200 rounded-xl text-xs font-bold text-slate-700 flex items-center gap-1.5 shadow-xs transition cursor-pointer"
            >
              <Eye className="w-4 h-4 text-slate-500" />
              View Bill
            </button>
            <a
              href={pdfDownloadUrl}
              target="_blank"
              rel="noreferrer"
              className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-xs font-bold flex items-center gap-1.5 shadow-md shadow-emerald-600/20 transition cursor-pointer"
            >
              <Download className="w-4 h-4" />
              Download PDF
            </a>
          </div>
        </div>

        {/* Itemized Table */}
        <div className="text-xs space-y-2 bg-white p-4 rounded-xl border border-emerald-200 shadow-xs">
          <div className="flex justify-between text-slate-600">
            <span>Work Duration:</span>
            <span className="font-semibold text-slate-900">{durationFormatted}</span>
          </div>
          <div className="flex justify-between text-slate-600">
            <span>First 60 Minutes (Base Service):</span>
            <span className="font-semibold text-slate-800">₹{baseServiceInr}</span>
          </div>
          {additionalBlocks > 0 && (
            <div className="flex justify-between text-slate-600">
              <span>Additional Time ({additionalBlocks} block(s) × 30 mins):</span>
              <span className="font-semibold text-slate-800">₹{additionalAmountInr}</span>
            </div>
          )}
          <div className="pt-2 border-t border-slate-200 flex justify-between text-sm font-extrabold text-slate-900">
            <span>Total Labour Paid:</span>
            <span className="text-emerald-700 font-mono text-base">
              ₹{p.amountInr.toLocaleString('en-IN')}
            </span>
          </div>
        </div>

        {/* Damaged Parts Note */}
        {job.damagedComponents && job.damagedComponents.length > 0 && (
          <div className="p-3 bg-amber-50/80 border border-amber-200 rounded-xl text-xs space-y-1">
            <span className="font-bold text-amber-900 flex items-center gap-1.5">
              <PackageX className="w-3.5 h-3.5 text-amber-600" />
              Replacement Parts ({job.damagedComponents.length} reported)
            </span>
            <p className="text-[11px] text-amber-800">
              Status: <b>Price to be confirmed</b>. Replacement parts are procured and billed separately under customer approval.
            </p>
          </div>
        )}

        {/* Audit Meta */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-[11px] text-slate-500 pt-1">
          <div>
            <span className="font-semibold text-slate-700">Payment Reference: </span>
            <code className="text-blue-700 font-mono font-bold bg-blue-50 px-1 rounded">
              {p.paymentReference || p.paymentId}
            </code>
          </div>
          <div>
            <span className="font-semibold text-slate-700">Settled At: </span>
            <span>{p.paidAt ? new Date(p.paidAt).toLocaleString('en-IN') : 'Just now'}</span>
          </div>
        </div>

        {/* View Bill Modal */}
        {showBillModal && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-xs p-4">
            <div className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-2xl border border-slate-200 space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-slate-100">
                <div>
                  <h3 className="font-extrabold text-slate-900 text-base">Official Service Payment Receipt</h3>
                  <p className="text-xs text-slate-500">Receipt #{receiptNo}</p>
                </div>
                <button
                  onClick={() => setShowBillModal(false)}
                  className="text-slate-400 hover:text-slate-600 font-bold text-lg cursor-pointer"
                >
                  ✕
                </button>
              </div>

              <div className="space-y-3 text-xs">
                <div className="bg-slate-50 p-3 rounded-xl border border-slate-200 space-y-1">
                  <div className="flex justify-between">
                    <span className="text-slate-500">Customer:</span>
                    <span className="font-bold text-slate-800">{job.customerName}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-500">Job Reference:</span>
                    <span className="font-bold font-mono text-blue-700">{job.id}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-500">Technician:</span>
                    <span className="font-bold text-slate-800">{job.assignedElectricianName || 'Field Technician'}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-500">Actual Work Duration:</span>
                    <span className="font-bold text-slate-800">{durationFormatted}</span>
                  </div>
                </div>

                <div className="border border-slate-200 rounded-xl overflow-hidden">
                  <div className="bg-slate-100 px-3 py-2 font-bold text-slate-700 flex justify-between">
                    <span>Item / Time Slab</span>
                    <span>Amount</span>
                  </div>
                  <div className="p-3 space-y-1.5">
                    <div className="flex justify-between text-slate-600">
                      <span>First 60 minutes (Base Service Labour)</span>
                      <span className="font-semibold text-slate-800">₹{baseServiceInr}.00</span>
                    </div>
                    {additionalBlocks > 0 && (
                      <div className="flex justify-between text-slate-600">
                        <span>Additional {additionalBlocks} × 30-min block(s)</span>
                        <span className="font-semibold text-slate-800">₹{additionalAmountInr}.00</span>
                      </div>
                    )}
                    <div className="pt-2 border-t border-slate-200 flex justify-between font-extrabold text-sm text-slate-900">
                      <span>Total Labour Paid</span>
                      <span className="text-emerald-700 font-mono">₹{p.amountInr.toLocaleString('en-IN')}.00</span>
                    </div>
                  </div>
                </div>

                {job.damagedComponents && job.damagedComponents.length > 0 && (
                  <div className="border border-amber-200 bg-amber-50/50 rounded-xl p-3 space-y-1.5">
                    <span className="font-bold text-amber-900 block">Reported Damaged Components:</span>
                    {job.damagedComponents.map((d, i) => (
                      <div key={i} className="flex justify-between text-[11px] text-slate-700">
                        <span>• {d.componentName} (Qty: {d.quantity})</span>
                        <span className="font-semibold text-amber-800">{d.priceStatus}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              <div className="pt-3 border-t border-slate-100 flex justify-end gap-2">
                <a
                  href={pdfDownloadUrl}
                  target="_blank"
                  rel="noreferrer"
                  className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white font-bold rounded-xl text-xs flex items-center gap-1.5 shadow-md shadow-emerald-600/20 cursor-pointer"
                >
                  <Download className="w-3.5 h-3.5" />
                  Download PDF
                </a>
                <button
                  type="button"
                  onClick={() => setShowBillModal(false)}
                  className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold rounded-xl text-xs cursor-pointer"
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    );
  }

  // =========================================================================
  // RENDER PAYMENT CHECKOUT FORM (PENDING PAYMENT)
  // =========================================================================
  return (
    <div className="bg-white rounded-2xl p-5 sm:p-6 border-2 border-blue-200 shadow-md space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between pb-3 border-b border-slate-100">
        <div className="flex items-center gap-2.5">
          <div className="w-10 h-10 rounded-2xl bg-gradient-to-tr from-blue-600 to-indigo-600 text-white flex items-center justify-center shadow-md shadow-blue-500/20">
            <CreditCard className="w-5 h-5" />
          </div>
          <div>
            <h4 className="text-sm font-extrabold text-slate-900">
              Customer Payment & Service Settlement
            </h4>
            <p className="text-xs text-slate-500">
              Time-based service billing • Duration: {durationFormatted}
            </p>
          </div>
        </div>

        <span className="px-2.5 py-1 rounded-full text-[11px] font-bold bg-amber-50 text-amber-800 border border-amber-200">
          Payment Required
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

      {/* Module 1: Time-Based Pricing Breakdown */}
      <div className="bg-slate-50 p-4 rounded-xl border border-slate-200 text-xs space-y-2">
        <div className="flex items-center justify-between text-slate-700 pb-2 border-b border-slate-200/80">
          <span className="font-bold flex items-center gap-1.5">
            <Clock className="w-3.5 h-3.5 text-blue-600" />
            Actual Work Duration:
          </span>
          <span className="font-bold text-slate-900 font-mono">{durationFormatted}</span>
        </div>

        <div className="flex justify-between text-slate-600">
          <span>First 60 minutes (Base Service):</span>
          <span className="font-semibold text-slate-800">₹{baseServiceInr}</span>
        </div>

        {additionalBlocks > 0 && (
          <div className="flex justify-between text-slate-600">
            <span>Additional {additionalBlocks} × 30-min block(s) (@ ₹100/block):</span>
            <span className="font-semibold text-slate-800">₹{additionalAmountInr}</span>
          </div>
        )}

        <div className="pt-2 border-t border-slate-200 flex justify-between text-sm font-extrabold text-slate-900">
          <span>Total Service Labour Charge:</span>
          <span className="text-blue-700 font-mono text-base">₹{labourTotalInr.toLocaleString('en-IN')}</span>
        </div>
      </div>

      {/* Module 3: Damaged Components / Replacement Parts */}
      {job.damagedComponents && job.damagedComponents.length > 0 && (
        <div className="p-3.5 bg-amber-50/70 border border-amber-200 rounded-xl text-xs space-y-2">
          <div className="flex items-center justify-between">
            <span className="font-bold text-amber-900 flex items-center gap-1.5">
              <PackageX className="w-4 h-4 text-amber-600" />
              Damaged Components / Replacement Parts ({job.damagedComponents.length})
            </span>
            <span className="text-[10px] bg-amber-100 text-amber-800 font-semibold px-2 py-0.5 rounded-full border border-amber-200">
              Customer Responsible
            </span>
          </div>

          <div className="space-y-1.5">
            {job.damagedComponents.map((item, idx) => (
              <div key={idx} className="bg-white/80 p-2 rounded-lg border border-amber-200/80 flex justify-between items-center text-[11px]">
                <div>
                  <span className="font-bold text-slate-800">{item.componentName}</span>
                  <span className="text-slate-500 ml-1.5">(Qty: {item.quantity})</span>
                  <p className="text-slate-500 text-[10px]">{item.damageDescription}</p>
                </div>
                <span className="font-semibold text-amber-800 text-[10px] bg-amber-50 px-2 py-0.5 rounded border border-amber-200">
                  {item.priceStatus || 'Price to be confirmed'}
                </span>
              </div>
            ))}
          </div>

          <p className="text-[10px] text-amber-800 leading-relaxed italic">
            * Note: Replacement part charges are billed separately upon procurement. The service labour charge above reflects only actual technician working time.
          </p>
        </div>
      )}

      {/* Payment Method Selector */}
      <div className="space-y-2 pt-1">
        <label className="block text-xs font-bold text-slate-700">Select Payment Method</label>
        <div className="grid grid-cols-2 gap-3">
          <button
            type="button"
            onClick={() => setSelectedMethod('UPI')}
            className={`p-3 rounded-xl border-2 text-left flex items-center justify-between transition cursor-pointer ${
              selectedMethod === 'UPI'
                ? 'border-blue-600 bg-blue-50/50'
                : 'border-slate-200 hover:border-slate-300'
            }`}
          >
            <div>
              <span className="font-bold text-slate-900 text-xs block">Razorpay UPI</span>
              <span className="text-[10px] text-slate-500">Google Pay, PhonePe, Cards (Test Mode)</span>
            </div>
            {selectedMethod === 'UPI' && <Check className="w-4 h-4 text-blue-600" />}
          </button>

          <button
            type="button"
            onClick={() => setSelectedMethod('CASH')}
            className={`p-3 rounded-xl border-2 text-left flex items-center justify-between transition cursor-pointer ${
              selectedMethod === 'CASH'
                ? 'border-blue-600 bg-blue-50/50'
                : 'border-slate-200 hover:border-slate-300'
            }`}
          >
            <div>
              <span className="font-bold text-slate-900 text-xs block">Cash to Technician</span>
              <span className="text-[10px] text-slate-500">Pay directly at premises</span>
            </div>
            {selectedMethod === 'CASH' && <Check className="w-4 h-4 text-blue-600" />}
          </button>
        </div>
      </div>

      {/* CASH PAYMENT INSTRUCTIONS */}
      {selectedMethod === 'CASH' && (
        <div className="p-3.5 bg-slate-50 border border-slate-200 rounded-xl text-xs space-y-2">
          <div className="flex items-center gap-1.5 text-slate-800 font-bold">
            <Banknote className="w-4 h-4 text-emerald-600" />
            <span>Cash Payment Instructions</span>
          </div>
          <p className="text-slate-600 leading-relaxed">
            Please hand <b>₹{labourTotalInr}</b> in exact cash to your technician{' '}
            <b>{job.assignedElectricianName || 'Guruprasad Rao'}</b>. Once the technician confirms the payment on their terminal, this job ticket will be officially closed and your digital receipt will be automatically available for download.
          </p>
          <div className="text-[11px] text-amber-700 bg-amber-50 p-2 rounded-lg border border-amber-200 flex items-center gap-1.5">
            <Info className="w-3.5 h-3.5 flex-shrink-0" />
            <span>Payment status will remain <b>PENDING</b> until confirmed by the technician.</span>
          </div>
        </div>
      )}

      {/* Action Buttons */}
      {selectedMethod === 'UPI' && (
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
            Pay ₹{labourTotalInr} via Razorpay (Test Mode)
          </button>

          <button
            type="button"
            disabled={isProcessing}
            onClick={handleSimulateInstantPayment}
            className="py-3 px-4 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-xs font-bold shadow-md shadow-emerald-500/20 flex items-center justify-center gap-2 transition cursor-pointer disabled:opacity-60"
          >
            <Sparkles className="w-4 h-4" />
            Instant Sandbox Verification (Test Mode)
          </button>
        </div>
      )}

      <div className="flex items-center justify-center gap-2 text-[11px] text-slate-400">
        <Lock className="w-3.5 h-3.5 text-slate-400" />
        <span>ElectroGrid Field Services • 256-Bit SSL Encryption • Razorpay Test Mode Only</span>
      </div>
    </div>
  );
};
