import React from 'react';
import { Box, Paper, Typography, List, ListItem, ListItemText, Divider, IconButton } from '@mui/material';
import { Delete as DeleteIcon } from '@mui/icons-material';
import { format, startOfWeek, endOfWeek, startOfMonth, endOfMonth, addDays, isWithinInterval } from 'date-fns';
import type { Event } from '@/lib/api';

interface EventListProps {
  events: Event[];
  date: Date;
  dateRange: 'day' | 'week' | 'month';
  onDeleteEvent?: (eventId: string) => void;
}

export default function EventList({ events, date, dateRange, onDeleteEvent }: EventListProps) {
  // Filter events based on the selected date range
  const filteredEvents = events.filter(event => {
    const eventDate = new Date(event.start_time);
    
    if (dateRange === 'day') {
      return (
        eventDate.getFullYear() === date.getFullYear() &&
        eventDate.getMonth() === date.getMonth() &&
        eventDate.getDate() === date.getDate()
      );
    } else if (dateRange === 'week') {
      const weekStart = startOfWeek(date);
      const weekEnd = endOfWeek(date);
      return isWithinInterval(eventDate, { start: weekStart, end: weekEnd });
    } else if (dateRange === 'month') {
      const monthStart = startOfMonth(date);
      const monthEnd = endOfMonth(date);
      return isWithinInterval(eventDate, { start: monthStart, end: monthEnd });
    }
    
    return false;
  }).sort((a, b) => new Date(a.start_time).getTime() - new Date(b.start_time).getTime());

  const handleDelete = (eventId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (onDeleteEvent) {
      if (window.confirm('Are you sure you want to delete this event?')) {
        onDeleteEvent(eventId);
      }
    }
  };

  const getDateRangeLabel = () => {
    if (dateRange === 'day') {
      return format(date, 'MMMM d, yyyy');
    } else if (dateRange === 'week') {
      const weekStart = startOfWeek(date);
      const weekEnd = endOfWeek(date);
      return `${format(weekStart, 'MMM d')} - ${format(weekEnd, 'MMM d, yyyy')}`;
    } else if (dateRange === 'month') {
      return format(date, 'MMMM yyyy');
    }
    return '';
  };

  return (
    <Paper elevation={0} sx={{ p: 2 }}>
      <Typography variant="h6" gutterBottom>
        Events for {getDateRangeLabel()}
      </Typography>
      
      {filteredEvents.length === 0 ? (
        <Typography color="text.secondary" align="center" sx={{ py: 4 }}>
          No events scheduled for this {dateRange}
        </Typography>
      ) : (
        <List sx={{ width: '100%' }}>
          {filteredEvents.map((event, index) => (
            <React.Fragment key={event.id}>
              <ListItem alignItems="flex-start" 
                sx={{ 
                  position: 'relative',
                  '&:hover .delete-button': {
                    opacity: 1,
                  }
                }}
              >
                <ListItemText
                  primary={
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <Typography
                        component="div"
                        variant="body2"
                        color="text.secondary"
                        sx={{ minWidth: 100 }}
                      >
                        {format(new Date(event.start_time), 'h:mm a')}
                      </Typography>
                      <Typography component="div" variant="subtitle1">
                        {event.title}
                      </Typography>
                    </Box>
                  }
                  secondary={
                    <Box sx={{ ml: '100px' }}>
                      {dateRange !== 'day' && (
                        <Typography component="div" variant="body2" display="block" color="text.secondary">
                          {format(new Date(event.start_time), 'EEE, MMM d')}
                        </Typography>
                      )}
                      {event.location && (
                        <Typography component="div" variant="body2" display="block">
                          📍 {event.location}
                        </Typography>
                      )}
                      {event.participants.length > 0 && (
                        <Typography component="div" variant="body2" display="block">
                          👥 {event.participants.join(', ')}
                        </Typography>
                      )}
                      {event.description && (
                        <Typography
                          component="div"
                          variant="body2"
                          color="text.secondary"
                          display="block"
                          sx={{
                            mt: 0.5,
                            whiteSpace: 'pre-wrap',
                            overflow: 'hidden',
                            textOverflow: 'ellipsis',
                            display: '-webkit-box',
                            WebkitLineClamp: 2,
                            WebkitBoxOrient: 'vertical',
                          }}
                        >
                          {event.description}
                        </Typography>
                      )}
                    </Box>
                  }
                />
                
                {onDeleteEvent && (
                  <IconButton 
                    className="delete-button"
                    color="error" 
                    size="small" 
                    aria-label="Delete event" 
                    onClick={(e) => handleDelete(event.id, e)}
                    sx={{ 
                      position: 'absolute',
                      right: 8,
                      top: 8,
                      opacity: 0,
                      transition: 'opacity 0.2s'
                    }}
                  >
                    <DeleteIcon fontSize="small" />
                  </IconButton>
                )}
              </ListItem>
              {index < filteredEvents.length - 1 && <Divider component="li" />}
            </React.Fragment>
          ))}
        </List>
      )}
    </Paper>
  );
}
