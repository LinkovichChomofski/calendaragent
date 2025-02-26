import React, { useState, useEffect } from 'react';
import { Box, Paper, IconButton, Typography, useTheme } from '@mui/material';
import { DateCalendar } from '@mui/x-date-pickers/DateCalendar';
import { LocalizationProvider } from '@mui/x-date-pickers/LocalizationProvider';
import { AdapterDateFns } from '@mui/x-date-pickers/AdapterDateFns';
import { ChevronLeft, ChevronRight } from '@mui/icons-material';
import { format, addMonths, subMonths, isSameDay } from 'date-fns';
import { PickersDay, PickersDayProps } from '@mui/x-date-pickers';
import type { Event } from '@/lib/api';

interface CalendarProps {
  events: Event[];
  onDateSelect: (date: Date) => void;
  selectedDate: Date;
}

export default function Calendar({ events, onDateSelect, selectedDate }: CalendarProps) {
  const theme = useTheme();
  const [currentMonth, setCurrentMonth] = useState<Date | null>(null);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setCurrentMonth(new Date());
    setMounted(true);
  }, []);

  if (!mounted || !currentMonth) {
    return null;
  }

  const handlePrevMonth = () => {
    setCurrentMonth(subMonths(currentMonth, 1));
  };

  const handleNextMonth = () => {
    setCurrentMonth(addMonths(currentMonth, 1));
  };

  const ServerDay = React.forwardRef((props: PickersDayProps<Date>, ref: React.Ref<HTMLButtonElement>) => {
    const { day, outsideCurrentMonth = false, ...other } = props;

    const dayEvents = events.filter(event => 
      isSameDay(new Date(event.start_time), day)
    );

    const isSelected = isSameDay(day, selectedDate);

    return (
      <Box
        sx={{
          position: 'relative',
          width: '36px',
          height: '36px',
        }}
      >
        <PickersDay 
          {...other} 
          ref={ref}
          day={day}
          outsideCurrentMonth={outsideCurrentMonth}
          selected={isSelected}
          sx={{
            ...(!outsideCurrentMonth && dayEvents.length > 0 && {
              backgroundColor: theme.palette.primary.light,
              color: theme.palette.primary.contrastText,
              '&:hover': {
                backgroundColor: theme.palette.primary.main,
              },
            }),
            ...(isSelected && {
              backgroundColor: `${theme.palette.primary.main} !important`,
              color: `${theme.palette.primary.contrastText} !important`,
            }),
          }}
          onClick={() => onDateSelect(day)}
        />
        {!outsideCurrentMonth && dayEvents.length > 0 && (
          <Box
            sx={{
              position: 'absolute',
              bottom: '2px',
              left: '50%',
              transform: 'translateX(-50%)',
              width: '4px',
              height: '4px',
              borderRadius: '50%',
              backgroundColor: isSelected ? theme.palette.primary.contrastText : theme.palette.primary.main,
            }}
          />
        )}
      </Box>
    );
  });

  ServerDay.displayName = 'ServerDay';

  return (
    <Paper elevation={3} sx={{ p: 2, height: '100%' }}>
      <Box sx={{ mb: 2, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <Typography variant="h6">{format(currentMonth, 'MMMM yyyy')}</Typography>
        <Box>
          <IconButton onClick={handlePrevMonth} size="small">
            <ChevronLeft />
          </IconButton>
          <IconButton onClick={handleNextMonth} size="small">
            <ChevronRight />
          </IconButton>
        </Box>
      </Box>
      
      <LocalizationProvider dateAdapter={AdapterDateFns}>
        <DateCalendar
          value={selectedDate}
          onChange={(newDate) => newDate && onDateSelect(newDate)}
          slots={{
            day: ServerDay as React.ComponentType<PickersDayProps<Date>>
          }}
          sx={{
            width: '100%',
            '& .MuiPickersDay-root': {
              fontSize: '0.875rem',
            },
          }}
        />
      </LocalizationProvider>
    </Paper>
  );
}
