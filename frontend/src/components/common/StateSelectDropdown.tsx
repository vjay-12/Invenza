import React, { useState, useRef, useEffect } from 'react';
import { IconChevronDown, IconCheck } from '../icons';

interface StateOption {
  code: string;
  name: string;
  label: string;
}

const STATE_OPTIONS: StateOption[] = [
  { code: '29', name: 'Karnataka', label: '29 - Karnataka (Intra-State CGST+SGST)' },
  { code: '33', name: 'Tamil Nadu', label: '33 - Tamil Nadu (Inter-State IGST)' },
  { code: '27', name: 'Maharashtra', label: '27 - Maharashtra (Inter-State IGST)' },
  { code: '07', name: 'Delhi', label: '07 - Delhi (Inter-State IGST)' },
  { code: '36', name: 'Telangana', label: '36 - Telangana (Inter-State IGST)' },
  { code: '24', name: 'Gujarat', label: '24 - Gujarat (Inter-State IGST)' },
  { code: '32', name: 'Kerala', label: '32 - Kerala (Inter-State IGST)' },
  { code: '19', name: 'West Bengal', label: '19 - West Bengal (Inter-State IGST)' },
];

interface StateSelectDropdownProps {
  selectedCode: string;
  onSelect: (code: string, name: string) => void;
  disabled?: boolean;
}

export const StateSelectDropdown: React.FC<StateSelectDropdownProps> = ({
  selectedCode,
  onSelect,
  disabled = false,
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const selectedState = STATE_OPTIONS.find((s) => s.code === selectedCode) || STATE_OPTIONS[0];

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setIsOpen(false);
      }
    };

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
      document.addEventListener('keydown', handleKeyDown);
    }
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [isOpen]);

  return (
    <div className="relative w-full" ref={dropdownRef}>
      <button
        type="button"
        disabled={disabled}
        onClick={() => setIsOpen((prev) => !prev)}
        aria-expanded={isOpen}
        aria-haspopup="listbox"
        className={`w-full flex items-center justify-between gap-2 px-2.5 py-1.5 h-[34px] rounded-lg border text-xs transition-colors text-left cursor-pointer focus:outline-none focus:ring-1 focus:ring-teal-600 select-none ${
          isOpen
            ? 'border-teal-500/60 bg-teal-500/5 text-slate-900 dark:text-slate-100 shadow-sm'
            : 'border-slate-200 dark:border-slate-800 bg-white dark:bg-[#131924] text-slate-800 dark:text-slate-200 hover:border-slate-300 dark:hover:border-slate-700'
        }`}
      >
        <span className="truncate font-mono text-[11px] text-slate-800 dark:text-slate-200">
          {selectedState.label}
        </span>
        <IconChevronDown
          className={`h-3.5 w-3.5 shrink-0 text-slate-400 transition-transform duration-200 ${
            isOpen ? 'rotate-180 text-teal-500' : ''
          }`}
        />
      </button>

      {isOpen && (
        <div
          role="listbox"
          className="absolute left-0 top-full mt-1 w-full min-w-[280px] sm:min-w-[320px] z-50 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-[#111622] shadow-2xl ring-1 ring-black/5 dark:ring-white/10 p-1.5 space-y-0.5 animate-in fade-in zoom-in-95 duration-150"
        >
          <div className="px-2.5 py-1 text-[10px] font-mono font-bold uppercase tracking-wider text-slate-400 dark:text-slate-500 border-b border-slate-100 dark:border-slate-800 mb-1">
            Place of Supply / GST State
          </div>
          {STATE_OPTIONS.map((st) => {
            const isSelected = st.code === selectedState.code;
            return (
              <button
                key={st.code}
                type="button"
                role="option"
                aria-selected={isSelected}
                onClick={() => {
                  onSelect(st.code, st.name);
                  setIsOpen(false);
                }}
                className={`w-full flex items-center justify-between px-2.5 py-2 rounded-lg text-left transition-colors text-xs font-mono cursor-pointer ${
                  isSelected
                    ? 'bg-teal-500/15 text-teal-700 dark:text-teal-300 font-semibold border border-teal-500/30'
                    : 'text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800/80 border border-transparent'
                }`}
              >
                <span className="truncate">{st.label}</span>
                {isSelected && (
                  <IconCheck className="h-3.5 w-3.5 text-teal-600 dark:text-teal-400 shrink-0" />
                )}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
};
