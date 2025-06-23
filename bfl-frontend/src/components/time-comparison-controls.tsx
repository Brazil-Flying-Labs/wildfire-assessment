"use client"

import { useState, useMemo, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { Calendar } from '@/components/ui/calendar'
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover'
import { CalendarIcon } from 'lucide-react'
import { cn } from '@/lib/utils'
import { format } from 'date-fns'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

export interface TimeComparisonControlsProps {
  onChange?: (fromDate: Date | undefined, toDate: Date | undefined) => void
  className?: string
  availableDates?: Date[]
}

export function TimeComparisonControls({
  onChange,
  className,
  availableDates = [],
}: TimeComparisonControlsProps) {
  const [fromDate, setFromDate] = useState<Date>()
  const [toDate, setToDate] = useState<Date>()

  // Pre-compute valid dates set for disabling calendar days
  const availableSet = useMemo(
    () => new Set(availableDates.map(d => format(d, 'yyyy-MM-dd'))),
    [availableDates]
  )

  // Auto-apply when both dates are selected
  useEffect(() => {
    if (fromDate && toDate && onChange) {
      onChange(fromDate, toDate)
    }
  }, [fromDate, toDate, onChange])

  // Handle date changes
  const handleFromDateChange = (date: Date | undefined) => {
    setFromDate(date)
  }

  const handleToDateChange = (date: Date | undefined) => {
    setToDate(date)
  }

  // Quick selection buttons
  const setLastMonth = () => {
    const now = new Date()
    const lastMonth = new Date(now.getFullYear(), now.getMonth() - 1, 1)
    const thisMonth = new Date(now.getFullYear(), now.getMonth(), 1)
    
    setFromDate(lastMonth)
    setToDate(thisMonth)
    // Trigger apply for quick selection
    if (onChange) {
      onChange(lastMonth, thisMonth)
    }
  }

  const setLastYear = () => {
    const now = new Date()
    const lastYear = new Date(now.getFullYear() - 1, now.getMonth(), 1)
    const thisYear = new Date(now.getFullYear(), now.getMonth(), 1)
    
    setFromDate(lastYear)
    setToDate(thisYear)
    // Trigger apply for quick selection
    if (onChange) {
      onChange(lastYear, thisYear)
    }
  }

  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle className="text-lg">Time Period Comparison</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="flex flex-col space-y-4">
          <div className="flex space-x-2">
            <Button 
              variant="outline" 
              size="sm" 
              onClick={setLastMonth}
            >
              Last Month vs. Current
            </Button>
            <Button 
              variant="outline" 
              size="sm" 
              onClick={setLastYear}
            >
              Year-over-Year
            </Button>
          </div>
          
          <div className="flex flex-col sm:flex-row space-y-2 sm:space-y-0 sm:space-x-4">
            <div className="space-y-1">
              <div className="text-sm font-medium">Before Period:</div>
              <Popover>
                <PopoverTrigger asChild>
                  <Button
                    variant="outline"
                    className={cn(
                      "w-full justify-start text-left font-normal",
                      !fromDate && "text-muted-foreground"
                    )}
                  >
                    <CalendarIcon className="mr-2 h-4 w-4" />
                    {fromDate ? format(fromDate, "PPP") : "Select date"}
                  </Button>
                </PopoverTrigger>
                <PopoverContent className="w-auto p-0 z-[9999]" sideOffset={5} align="start">
                  <Calendar
                    mode="single"
                    selected={fromDate}
                    onSelect={handleFromDateChange}
                    initialFocus
                    disabled={(date: Date) => !availableSet.has(format(date, 'yyyy-MM-dd'))}
                  />
                </PopoverContent>
              </Popover>
            </div>
            
            <div className="space-y-1">
              <div className="text-sm font-medium">After Period:</div>
              <Popover>
                <PopoverTrigger asChild>
                  <Button
                    variant="outline"
                    className={cn(
                      "w-full justify-start text-left font-normal",
                      !toDate && "text-muted-foreground"
                    )}
                  >
                    <CalendarIcon className="mr-2 h-4 w-4" />
                    {toDate ? format(toDate, "PPP") : "Select date"}
                  </Button>
                </PopoverTrigger>
                <PopoverContent className="w-auto p-0 z-[9999]" sideOffset={5} align="start">
                  <Calendar
                    mode="single"
                    selected={toDate}
                    onSelect={handleToDateChange}
                    initialFocus
                    disabled={(date: Date) => !availableSet.has(format(date, 'yyyy-MM-dd'))}
                  />
                </PopoverContent>
              </Popover>
            </div>
          </div>

          <div className="flex justify-between items-center pt-2">
            <div className="text-sm text-muted-foreground">
              {fromDate && toDate ? 
                `Comparing ${format(fromDate, "MMM yyyy")} with ${format(toDate, "MMM yyyy")}` : 
                "Select both dates to compare periods"}
            </div>
            
            <Button 
              size="sm" 
              variant="default"
              disabled={!fromDate || !toDate}
              onClick={() => onChange && onChange(fromDate, toDate)}
            >
              Apply
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
