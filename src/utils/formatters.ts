/**
 * Indian Localization Utilities (Mysuru, Karnataka, India)
 * Enforces DD/MM/YYYY date formatting, IST time display, ₹ currency, and Indian phone standards.
 */

export function formatDateIST(dateStr?: string | Date | null): string {
  if (!dateStr) return 'N/A';
  try {
    const d = typeof dateStr === 'string' ? new Date(dateStr) : dateStr;
    if (isNaN(d.getTime())) return 'N/A';
    
    // Day, Month, Year
    const day = String(d.getDate()).padStart(2, '0');
    const month = String(d.getMonth() + 1).padStart(2, '0');
    const year = d.getFullYear();
    return `${day}/${month}/${year}`;
  } catch {
    return 'N/A';
  }
}

export function formatDateTimeIST(dateStr?: string | Date | null): string {
  if (!dateStr) return 'N/A';
  try {
    const d = typeof dateStr === 'string' ? new Date(dateStr) : dateStr;
    if (isNaN(d.getTime())) return 'N/A';

    const day = String(d.getDate()).padStart(2, '0');
    const month = String(d.getMonth() + 1).padStart(2, '0');
    const year = d.getFullYear();

    let hours = d.getHours();
    const minutes = String(d.getMinutes()).padStart(2, '0');
    const ampm = hours >= 12 ? 'PM' : 'AM';
    hours = hours % 12 || 12;

    return `${day}/${month}/${year}, ${hours}:${minutes} ${ampm} IST`;
  } catch {
    return 'N/A';
  }
}

export function formatTimeIST(dateStr?: string | Date | null): string {
  if (!dateStr) return 'N/A';
  try {
    const d = typeof dateStr === 'string' ? new Date(dateStr) : dateStr;
    if (isNaN(d.getTime())) return String(dateStr);

    let hours = d.getHours();
    const minutes = String(d.getMinutes()).padStart(2, '0');
    const ampm = hours >= 12 ? 'PM' : 'AM';
    hours = hours % 12 || 12;

    return `${hours}:${minutes} ${ampm} IST`;
  } catch {
    return String(dateStr);
  }
}

export function formatCurrencyINR(amount: number): string {
  return `₹${amount.toLocaleString('en-IN')}`;
}

export function formatIndianPhone(phone: string): string {
  if (!phone) return '+91 821 2419000';
  if (phone.startsWith('+91')) return phone;
  const digits = phone.replace(/\D/g, '');
  if (digits.length === 10) {
    return `+91 ${digits.slice(0, 5)} ${digits.slice(5)}`;
  }
  return phone;
}

