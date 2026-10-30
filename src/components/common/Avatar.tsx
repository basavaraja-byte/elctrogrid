import React, { useState } from 'react';

interface AvatarProps {
  src?: string;
  name: string;
  size?: 'xs' | 'sm' | 'md' | 'lg' | 'xl';
  className?: string;
  badge?: React.ReactNode;
}

const SIZE_MAP = {
  xs: 'w-6 h-6 text-[10px]',
  sm: 'w-8 h-8 text-xs',
  md: 'w-10 h-10 text-sm',
  lg: 'w-12 h-12 text-base',
  xl: 'w-16 h-16 text-xl',
};

const GRADIENTS = [
  'from-blue-600 to-indigo-600',
  'from-amber-600 to-orange-600',
  'from-emerald-600 to-teal-600',
  'from-purple-600 to-pink-600',
  'from-cyan-600 to-blue-600',
  'from-rose-600 to-red-600',
];

function getInitials(name: string): string {
  if (!name) return 'DG';
  const parts = name.trim().split(/\s+/);
  if (parts.length === 1) {
    return parts[0].slice(0, 2).toUpperCase();
  }
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}

function getGradient(name: string): string {
  let hash = 0;
  for (let i = 0; i < name.length; i++) {
    hash = name.charCodeAt(i) + ((hash << 5) - hash);
  }
  const idx = Math.abs(hash) % GRADIENTS.length;
  return GRADIENTS[idx];
}

export const Avatar: React.FC<AvatarProps> = ({
  src,
  name,
  size = 'md',
  className = '',
  badge,
}) => {
  const [hasError, setHasError] = useState(false);
  const initials = getInitials(name);
  const gradient = getGradient(name);
  const sizeClasses = SIZE_MAP[size];

  const showImage = src && !hasError && !src.includes('broken');

  return (
    <div className={`relative inline-flex items-center justify-center flex-shrink-0 ${className}`}>
      {showImage ? (
        <img
          src={src}
          alt={name}
          onError={() => setHasError(true)}
          className={`${sizeClasses} rounded-full object-cover border border-slate-200/80 shadow-xs`}
        />
      ) : (
        <div
          className={`${sizeClasses} rounded-full bg-gradient-to-tr ${gradient} text-white font-bold flex items-center justify-center shadow-xs select-none border border-white/20`}
          title={name}
        >
          {initials}
        </div>
      )}
      {badge && <div className="absolute -bottom-0.5 -right-0.5">{badge}</div>}
    </div>
  );
};

