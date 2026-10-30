export interface RazorpaySuccessPayload {
  razorpay_payment_id: string;
  razorpay_order_id: string;
  razorpay_signature: string;
}

export interface RazorpayOrderData {
  razorpay_key_id: string;
  amount_paise: number;
  currency: string;
  razorpay_order_id: string;
  booking_code: string;
  payment_code: string;
  customer_name: string;
  customer_email: string;
  customer_phone: string;
}

declare global {
  interface Window {
    Razorpay?: any;
  }
}

let scriptLoadingPromise: Promise<boolean> | null = null;

export function loadRazorpayCheckoutScript(): Promise<boolean> {
  if (typeof window !== 'undefined' && window.Razorpay) {
    return Promise.resolve(true);
  }
  if (scriptLoadingPromise) {
    return scriptLoadingPromise;
  }

  scriptLoadingPromise = new Promise((resolve) => {
    const script = document.createElement('script');
    script.src = 'https://checkout.razorpay.com/v1/checkout.js';
    script.async = true;
    script.onload = () => resolve(true);
    script.onerror = () => {
      scriptLoadingPromise = null;
      resolve(false);
    };
    document.body.appendChild(script);
  });

  return scriptLoadingPromise;
}

export async function openRazorpayStandardCheckout(
  order: RazorpayOrderData,
  callbacks: {
    onSuccess: (payload: RazorpaySuccessPayload) => void;
    onDismiss: () => void;
    onFailed: (reason: string) => void;
  }
): Promise<void> {
  const loaded = await loadRazorpayCheckoutScript();
  if (!loaded || !window.Razorpay) {
    throw new Error(
      'Unable to load Razorpay Checkout SDK from checkout.razorpay.com. Check your internet connection.'
    );
  }

  let completed = false;

  const instance = new window.Razorpay({
    key: order.razorpay_key_id,
    amount: order.amount_paise,
    currency: order.currency || 'INR',
    name: 'ElectroGrid Electrical Services',
    description: `Service Ticket ${order.booking_code}`,
    order_id: order.razorpay_order_id,
    prefill: {
      name: order.customer_name,
      email: order.customer_email,
      contact: order.customer_phone,
    },
    notes: {
      booking_code: order.booking_code,
      payment_code: order.payment_code,
    },
    theme: {
      color: '#2563eb',
    },
    handler: (response: Record<string, unknown>) => {
      completed = true;
      callbacks.onSuccess({
        razorpay_payment_id: String(response.razorpay_payment_id || ''),
        razorpay_order_id: String(response.razorpay_order_id || ''),
        razorpay_signature: String(response.razorpay_signature || ''),
      });
    },
    modal: {
      ondismiss: () => {
        if (!completed) {
          callbacks.onDismiss();
        }
      },
    },
  });

  instance.on('payment.failed', (resp: Record<string, unknown>) => {
    completed = true;
    const errObj = (resp.error || {}) as Record<string, unknown>;
    const desc = String(
      errObj.description || errObj.reason || 'Payment declined during Razorpay checkout.'
    );
    callbacks.onFailed(desc);
  });

  instance.open();
}

