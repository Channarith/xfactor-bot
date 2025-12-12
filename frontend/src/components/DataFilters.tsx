import { useState, useMemo, useCallback } from 'react'
import { 
  Search, SortAsc, SortDesc, Filter, X, ChevronDown, 
  Calendar, DollarSign, Hash, Type, BarChart2
} from 'lucide-react'

// ============================================================================
// Types
// ============================================================================

export type SortDirection = 'asc' | 'desc' | null

export interface SortConfig {
  field: string
  direction: SortDirection
}

export interface FilterConfig {
  field: string
  operator: 'eq' | 'neq' | 'gt' | 'gte' | 'lt' | 'lte' | 'contains' | 'startsWith' | 'endsWith' | 'in' | 'between'
  value: any
  label?: string
}

export interface FieldDefinition {
  key: string
  label: string
  type: 'string' | 'number' | 'date' | 'boolean' | 'select'
  sortable?: boolean
  filterable?: boolean
  options?: { value: string; label: string }[]  // For select type
}

export interface DataFiltersProps<T> {
  data: T[]
  fields: FieldDefinition[]
  onFilteredData: (data: T[]) => void
  placeholder?: string
  showSearch?: boolean
  showSort?: boolean
  showFilters?: boolean
  compact?: boolean
}

// ============================================================================
// Utility Functions
// ============================================================================

export function applyFilters<T>(
  data: T[],
  searchQuery: string,
  searchFields: string[],
  filters: FilterConfig[],
  sort: SortConfig | null
): T[] {
  let result = [...data]

  // Apply search
  if (searchQuery.trim()) {
    const query = searchQuery.toLowerCase()
    result = result.filter(item => 
      searchFields.some(field => {
        const value = getNestedValue(item, field)
        return value !== null && value !== undefined && 
               String(value).toLowerCase().includes(query)
      })
    )
  }

  // Apply filters
  for (const filter of filters) {
    result = result.filter(item => {
      const value = getNestedValue(item, filter.field)
      return applyFilterOperator(value, filter.operator, filter.value)
    })
  }

  // Apply sort
  if (sort && sort.direction) {
    result.sort((a, b) => {
      const aVal = getNestedValue(a, sort.field)
      const bVal = getNestedValue(b, sort.field)
      
      if (aVal === null || aVal === undefined) return 1
      if (bVal === null || bVal === undefined) return -1
      
      let comparison = 0
      if (typeof aVal === 'string' && typeof bVal === 'string') {
        comparison = aVal.localeCompare(bVal)
      } else if (typeof aVal === 'number' && typeof bVal === 'number') {
        comparison = aVal - bVal
      } else if (aVal instanceof Date && bVal instanceof Date) {
        comparison = aVal.getTime() - bVal.getTime()
      } else {
        comparison = String(aVal).localeCompare(String(bVal))
      }
      
      return sort.direction === 'desc' ? -comparison : comparison
    })
  }

  return result
}

function getNestedValue(obj: any, path: string): any {
  return path.split('.').reduce((acc, part) => acc?.[part], obj)
}

function applyFilterOperator(value: any, operator: FilterConfig['operator'], filterValue: any): boolean {
  if (value === null || value === undefined) return false
  
  switch (operator) {
    case 'eq':
      return value === filterValue
    case 'neq':
      return value !== filterValue
    case 'gt':
      return value > filterValue
    case 'gte':
      return value >= filterValue
    case 'lt':
      return value < filterValue
    case 'lte':
      return value <= filterValue
    case 'contains':
      return String(value).toLowerCase().includes(String(filterValue).toLowerCase())
    case 'startsWith':
      return String(value).toLowerCase().startsWith(String(filterValue).toLowerCase())
    case 'endsWith':
      return String(value).toLowerCase().endsWith(String(filterValue).toLowerCase())
    case 'in':
      return Array.isArray(filterValue) && filterValue.includes(value)
    case 'between':
      return Array.isArray(filterValue) && filterValue.length === 2 && 
             value >= filterValue[0] && value <= filterValue[1]
    default:
      return true
  }
}

// ============================================================================
// Hook for Data Filtering
// ============================================================================

export function useDataFilters<T>(
  data: T[],
  fields: FieldDefinition[]
) {
  const [searchQuery, setSearchQuery] = useState('')
  const [sort, setSort] = useState<SortConfig | null>(null)
  const [filters, setFilters] = useState<FilterConfig[]>([])

  const searchFields = useMemo(() => 
    fields.filter(f => f.type === 'string').map(f => f.key),
    [fields]
  )

  const filteredData = useMemo(() => 
    applyFilters(data, searchQuery, searchFields, filters, sort),
    [data, searchQuery, searchFields, filters, sort]
  )

  const toggleSort = useCallback((field: string) => {
    setSort(prev => {
      if (prev?.field !== field) return { field, direction: 'asc' }
      if (prev.direction === 'asc') return { field, direction: 'desc' }
      if (prev.direction === 'desc') return null
      return { field, direction: 'asc' }
    })
  }, [])

  const addFilter = useCallback((filter: FilterConfig) => {
    setFilters(prev => [...prev, filter])
  }, [])

  const removeFilter = useCallback((index: number) => {
    setFilters(prev => prev.filter((_, i) => i !== index))
  }, [])

  const clearFilters = useCallback(() => {
    setFilters([])
    setSearchQuery('')
    setSort(null)
  }, [])

  return {
    filteredData,
    searchQuery,
    setSearchQuery,
    sort,
    setSort,
    toggleSort,
    filters,
    addFilter,
    removeFilter,
    clearFilters,
    totalCount: data.length,
    filteredCount: filteredData.length
  }
}

// ============================================================================
// Filter Bar Component
// ============================================================================

interface FilterBarProps {
  searchQuery: string
  onSearchChange: (query: string) => void
  sort: SortConfig | null
  onSortChange: (field: string) => void
  filters: FilterConfig[]
  onRemoveFilter: (index: number) => void
  onClearAll: () => void
  fields: FieldDefinition[]
  onAddFilter: (filter: FilterConfig) => void
  totalCount: number
  filteredCount: number
  placeholder?: string
  compact?: boolean
}

export function FilterBar({
  searchQuery,
  onSearchChange,
  sort,
  onSortChange,
  filters,
  onRemoveFilter,
  onClearAll,
  fields,
  onAddFilter,
  totalCount,
  filteredCount,
  placeholder = 'Search...',
  compact = false
}: FilterBarProps) {
  const [showFilterMenu, setShowFilterMenu] = useState(false)
  const [showSortMenu, setShowSortMenu] = useState(false)
  const [filterField, setFilterField] = useState<string>('')
  const [filterOperator, setFilterOperator] = useState<FilterConfig['operator']>('contains')
  const [filterValue, setFilterValue] = useState<string>('')

  const sortableFields = fields.filter(f => f.sortable !== false)
  const filterableFields = fields.filter(f => f.filterable !== false)

  const handleAddFilter = () => {
    if (filterField && filterValue) {
      const field = fields.find(f => f.key === filterField)
      let value: any = filterValue
      
      if (field?.type === 'number') {
        value = parseFloat(filterValue)
      } else if (field?.type === 'boolean') {
        value = filterValue === 'true'
      }
      
      onAddFilter({
        field: filterField,
        operator: filterOperator,
        value,
        label: `${field?.label || filterField} ${getOperatorLabel(filterOperator)} ${filterValue}`
      })
      
      setFilterField('')
      setFilterValue('')
      setShowFilterMenu(false)
    }
  }

  const getOperatorLabel = (op: FilterConfig['operator']): string => {
    switch (op) {
      case 'eq': return '='
      case 'neq': return '≠'
      case 'gt': return '>'
      case 'gte': return '≥'
      case 'lt': return '<'
      case 'lte': return '≤'
      case 'contains': return 'contains'
      case 'startsWith': return 'starts with'
      case 'endsWith': return 'ends with'
      case 'in': return 'in'
      case 'between': return 'between'
      default: return op
    }
  }

  const getFieldTypeIcon = (type: FieldDefinition['type']) => {
    switch (type) {
      case 'number': return <Hash className="h-3 w-3" />
      case 'date': return <Calendar className="h-3 w-3" />
      case 'string': return <Type className="h-3 w-3" />
      case 'select': return <BarChart2 className="h-3 w-3" />
      default: return null
    }
  }

  return (
    <div className={`space-y-2 ${compact ? 'mb-2' : 'mb-4'}`}>
      {/* Main Controls Row */}
      <div className="flex flex-wrap items-center gap-2">
        {/* Search Input */}
        <div className="relative flex-1 min-w-[200px]">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
            placeholder={placeholder}
            className="w-full pl-10 pr-4 py-2 text-sm rounded-lg bg-secondary border border-border focus:border-xfactor-teal focus:outline-none"
          />
          {searchQuery && (
            <button
              onClick={() => onSearchChange('')}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
            >
              <X className="h-4 w-4" />
            </button>
          )}
        </div>

        {/* Sort Dropdown */}
        <div className="relative">
          <button
            onClick={() => setShowSortMenu(!showSortMenu)}
            className={`flex items-center gap-2 px-3 py-2 text-sm rounded-lg border transition-colors ${
              sort ? 'bg-xfactor-teal/20 border-xfactor-teal text-xfactor-teal' : 'bg-secondary border-border hover:border-xfactor-teal/50'
            }`}
          >
            {sort?.direction === 'desc' ? <SortDesc className="h-4 w-4" /> : <SortAsc className="h-4 w-4" />}
            <span className="hidden sm:inline">
              {sort ? fields.find(f => f.key === sort.field)?.label || 'Sort' : 'Sort'}
            </span>
            <ChevronDown className="h-3 w-3" />
          </button>
          
          {showSortMenu && (
            <div className="absolute right-0 top-full mt-1 z-50 w-48 bg-card border border-border rounded-lg shadow-lg py-1">
              <div className="px-3 py-2 text-xs text-muted-foreground border-b border-border">Sort By</div>
              {sortableFields.map(field => (
                <button
                  key={field.key}
                  onClick={() => {
                    onSortChange(field.key)
                    setShowSortMenu(false)
                  }}
                  className={`w-full px-3 py-2 text-sm text-left hover:bg-secondary flex items-center justify-between ${
                    sort?.field === field.key ? 'text-xfactor-teal' : ''
                  }`}
                >
                  <span className="flex items-center gap-2">
                    {getFieldTypeIcon(field.type)}
                    {field.label}
                  </span>
                  {sort?.field === field.key && (
                    sort.direction === 'asc' ? <SortAsc className="h-4 w-4" /> : <SortDesc className="h-4 w-4" />
                  )}
                </button>
              ))}
              {sort && (
                <button
                  onClick={() => {
                    onSortChange(sort.field) // Toggle to null
                    setShowSortMenu(false)
                  }}
                  className="w-full px-3 py-2 text-sm text-left text-loss hover:bg-secondary border-t border-border"
                >
                  Clear Sort
                </button>
              )}
            </div>
          )}
        </div>

        {/* Filter Dropdown */}
        <div className="relative">
          <button
            onClick={() => setShowFilterMenu(!showFilterMenu)}
            className={`flex items-center gap-2 px-3 py-2 text-sm rounded-lg border transition-colors ${
              filters.length > 0 ? 'bg-xfactor-teal/20 border-xfactor-teal text-xfactor-teal' : 'bg-secondary border-border hover:border-xfactor-teal/50'
            }`}
          >
            <Filter className="h-4 w-4" />
            <span className="hidden sm:inline">Filter</span>
            {filters.length > 0 && (
              <span className="bg-xfactor-teal text-white text-xs px-1.5 rounded-full">{filters.length}</span>
            )}
            <ChevronDown className="h-3 w-3" />
          </button>
          
          {showFilterMenu && (
            <div className="absolute right-0 top-full mt-1 z-50 w-72 bg-card border border-border rounded-lg shadow-lg p-3">
              <div className="text-xs text-muted-foreground mb-2">Add Filter</div>
              
              {/* Field Select */}
              <select
                value={filterField}
                onChange={(e) => setFilterField(e.target.value)}
                className="w-full mb-2 px-3 py-2 text-sm rounded-lg bg-secondary border border-border"
              >
                <option value="">Select field...</option>
                {filterableFields.map(field => (
                  <option key={field.key} value={field.key}>{field.label}</option>
                ))}
              </select>
              
              {/* Operator Select */}
              {filterField && (
                <select
                  value={filterOperator}
                  onChange={(e) => setFilterOperator(e.target.value as FilterConfig['operator'])}
                  className="w-full mb-2 px-3 py-2 text-sm rounded-lg bg-secondary border border-border"
                >
                  <option value="contains">Contains</option>
                  <option value="eq">Equals</option>
                  <option value="neq">Not Equals</option>
                  {fields.find(f => f.key === filterField)?.type === 'number' && (
                    <>
                      <option value="gt">Greater Than</option>
                      <option value="gte">Greater or Equal</option>
                      <option value="lt">Less Than</option>
                      <option value="lte">Less or Equal</option>
                    </>
                  )}
                  <option value="startsWith">Starts With</option>
                  <option value="endsWith">Ends With</option>
                </select>
              )}
              
              {/* Value Input */}
              {filterField && (
                <>
                  {fields.find(f => f.key === filterField)?.type === 'select' ? (
                    <select
                      value={filterValue}
                      onChange={(e) => setFilterValue(e.target.value)}
                      className="w-full mb-2 px-3 py-2 text-sm rounded-lg bg-secondary border border-border"
                    >
                      <option value="">Select value...</option>
                      {fields.find(f => f.key === filterField)?.options?.map(opt => (
                        <option key={opt.value} value={opt.value}>{opt.label}</option>
                      ))}
                    </select>
                  ) : (
                    <input
                      type={fields.find(f => f.key === filterField)?.type === 'number' ? 'number' : 'text'}
                      value={filterValue}
                      onChange={(e) => setFilterValue(e.target.value)}
                      placeholder="Enter value..."
                      className="w-full mb-2 px-3 py-2 text-sm rounded-lg bg-secondary border border-border"
                    />
                  )}
                </>
              )}
              
              <button
                onClick={handleAddFilter}
                disabled={!filterField || !filterValue}
                className="w-full px-3 py-2 text-sm rounded-lg bg-xfactor-teal text-white hover:bg-xfactor-teal/80 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Add Filter
              </button>
            </div>
          )}
        </div>

        {/* Clear All */}
        {(searchQuery || sort || filters.length > 0) && (
          <button
            onClick={onClearAll}
            className="px-3 py-2 text-sm text-loss hover:text-loss/80"
          >
            Clear All
          </button>
        )}

        {/* Results Count */}
        <div className="text-xs text-muted-foreground ml-auto">
          {filteredCount === totalCount ? (
            <span>{totalCount} items</span>
          ) : (
            <span>{filteredCount} of {totalCount}</span>
          )}
        </div>
      </div>

      {/* Active Filters Row */}
      {filters.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {filters.map((filter, index) => (
            <span
              key={index}
              className="inline-flex items-center gap-1 px-2 py-1 text-xs rounded-full bg-xfactor-teal/20 text-xfactor-teal"
            >
              {filter.label || `${filter.field} ${filter.operator} ${filter.value}`}
              <button
                onClick={() => onRemoveFilter(index)}
                className="hover:text-white"
              >
                <X className="h-3 w-3" />
              </button>
            </span>
          ))}
        </div>
      )}
    </div>
  )
}

// ============================================================================
// Quick Filter Chips
// ============================================================================

interface QuickFilterProps {
  options: { label: string; filter: FilterConfig }[]
  activeFilters: FilterConfig[]
  onToggle: (filter: FilterConfig) => void
}

export function QuickFilters({ options, activeFilters, onToggle }: QuickFilterProps) {
  const isActive = (filter: FilterConfig) => 
    activeFilters.some(f => f.field === filter.field && f.value === filter.value)

  return (
    <div className="flex flex-wrap gap-2 mb-3">
      {options.map((opt, i) => (
        <button
          key={i}
          onClick={() => onToggle(opt.filter)}
          className={`px-3 py-1 text-xs rounded-full transition-colors ${
            isActive(opt.filter)
              ? 'bg-xfactor-teal text-white'
              : 'bg-secondary text-muted-foreground hover:text-foreground'
          }`}
        >
          {opt.label}
        </button>
      ))}
    </div>
  )
}

// ============================================================================
// Sortable Column Header
// ============================================================================

interface SortableHeaderProps {
  label: string
  field: string
  sort: SortConfig | null
  onSort: (field: string) => void
  className?: string
}

export function SortableHeader({ label, field, sort, onSort, className = '' }: SortableHeaderProps) {
  const isActive = sort?.field === field
  
  return (
    <button
      onClick={() => onSort(field)}
      className={`flex items-center gap-1 font-medium hover:text-xfactor-teal transition-colors ${
        isActive ? 'text-xfactor-teal' : ''
      } ${className}`}
    >
      {label}
      {isActive ? (
        sort.direction === 'asc' ? <SortAsc className="h-3 w-3" /> : <SortDesc className="h-3 w-3" />
      ) : (
        <SortAsc className="h-3 w-3 opacity-30" />
      )}
    </button>
  )
}

