import React, { useState, useMemo } from 'react';
import { Search, ChevronLeft, ChevronRight, Filter } from 'lucide-react';

export interface Column<T> {
  header: string;
  accessorKey?: keyof T;
  cell?: (row: T) => React.ReactNode;
  className?: string;
}

interface DataTableProps<T> {
  columns: Column<T>[];
  data: T[];
  searchPlaceholder?: string;
  searchFilter?: (item: T, query: string) => boolean;
  filterOptions?: {
    label: string;
    key: string;
    options: { label: string; value: string }[];
    filterFn: (item: T, value: string) => boolean;
  }[];
  pageSize?: number;
  emptyMessage?: string;
  onRowClick?: (row: T) => void;
}

export function DataTable<T extends { id?: string | number }>({
  columns,
  data,
  searchPlaceholder = 'Search records...',
  searchFilter,
  filterOptions = [],
  pageSize = 10,
  emptyMessage = 'No records found',
  onRowClick,
}: DataTableProps<T>) {
  const [searchQuery, setSearchQuery] = useState('');
  const [activeFilters, setActiveFilters] = useState<Record<string, string>>({});
  const [currentPage, setCurrentPage] = useState(1);

  const handleFilterChange = (key: string, value: string) => {
    setActiveFilters((prev) => ({ ...prev, [key]: value }));
    setCurrentPage(1);
  };

  const filteredData = useMemo(() => {
    return data.filter((item) => {
      // Search
      if (searchQuery.trim() && searchFilter) {
        if (!searchFilter(item, searchQuery.toLowerCase().trim())) {
          return false;
        }
      }

      // Dropdown filters
      for (const filter of filterOptions) {
        const selectedValue = activeFilters[filter.key];
        if (selectedValue && selectedValue !== 'all') {
          if (!filter.filterFn(item, selectedValue)) {
            return false;
          }
        }
      }

      return true;
    });
  }, [data, searchQuery, searchFilter, filterOptions, activeFilters]);

  // Pagination
  const totalPages = Math.max(1, Math.ceil(filteredData.length / pageSize));
  const paginatedData = useMemo(() => {
    const start = (currentPage - 1) * pageSize;
    return filteredData.slice(start, start + pageSize);
  }, [filteredData, currentPage, pageSize]);

  return (
    <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden flex flex-col">
      {/* Top Filter and Search Bar */}
      <div className="p-4 border-b border-slate-100 flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 bg-slate-50/50">
        <div className="relative flex-1 max-w-md">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => {
              setSearchQuery(e.target.value);
              setCurrentPage(1);
            }}
            placeholder={searchPlaceholder}
            className="w-full pl-9 pr-4 py-2 text-sm bg-white border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-600 transition"
          />
        </div>

        {filterOptions.length > 0 && (
          <div className="flex flex-wrap items-center gap-2">
            <Filter className="w-4 h-4 text-slate-400 mr-1 hidden sm:block" />
            {filterOptions.map((opt) => (
              <select
                key={opt.key}
                value={activeFilters[opt.key] || 'all'}
                onChange={(e) => handleFilterChange(opt.key, e.target.value)}
                className="text-xs bg-white border border-slate-200 text-slate-700 py-2 px-3 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-600"
              >
                <option value="all">All {opt.label}</option>
                {opt.options.map((o) => (
                  <option key={o.value} value={o.value}>
                    {o.label}
                  </option>
                ))}
              </select>
            ))}
          </div>
        )}
      </div>

      {/* Table Body */}
      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm text-slate-600">
          <thead className="bg-slate-50 border-b border-slate-200/80 text-xs uppercase font-semibold text-slate-500 tracking-wider">
            <tr>
              {columns.map((col, idx) => (
                <th key={idx} className={`py-3.5 px-4 ${col.className || ''}`}>
                  {col.header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {paginatedData.length > 0 ? (
              paginatedData.map((row, rowIdx) => (
                <tr
                  key={row.id || rowIdx}
                  onClick={() => onRowClick && onRowClick(row)}
                  className={`hover:bg-blue-50/40 transition-colors ${
                    onRowClick ? 'cursor-pointer' : ''
                  }`}
                >
                  {columns.map((col, colIdx) => (
                    <td key={colIdx} className={`py-3 px-4 ${col.className || ''}`}>
                      {col.cell
                        ? col.cell(row)
                        : col.accessorKey
                        ? (row[col.accessorKey] as React.ReactNode)
                        : null}
                    </td>
                  ))}
                </tr>
              ))
            ) : (
              <tr>
                <td
                  colSpan={columns.length}
                  className="py-12 text-center text-slate-400 text-sm"
                >
                  {emptyMessage}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination Footer */}
      <div className="px-4 py-3 border-t border-slate-100 bg-slate-50/50 flex items-center justify-between text-xs text-slate-500">
        <div>
          Showing{' '}
          <span className="font-semibold text-slate-700">
            {filteredData.length === 0 ? 0 : (currentPage - 1) * pageSize + 1}
          </span>{' '}
          to{' '}
          <span className="font-semibold text-slate-700">
            {Math.min(currentPage * pageSize, filteredData.length)}
          </span>{' '}
          of <span className="font-semibold text-slate-700">{filteredData.length}</span> results
        </div>

        <div className="flex items-center gap-1.5">
          <button
            onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
            disabled={currentPage === 1}
            className="p-1.5 rounded border border-slate-200 text-slate-600 disabled:opacity-40 disabled:cursor-not-allowed hover:bg-white"
          >
            <ChevronLeft className="w-4 h-4" />
          </button>
          <span className="px-2 font-medium text-slate-700">
            {currentPage} / {totalPages}
          </span>
          <button
            onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
            disabled={currentPage === totalPages}
            className="p-1.5 rounded border border-slate-200 text-slate-600 disabled:opacity-40 disabled:cursor-not-allowed hover:bg-white"
          >
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
}

