import React from 'react';
import { Box, Paper, Typography, List, ListItem, ListItemText, Divider } from '@mui/material';
import { format } from 'date-fns';
import type { Event } from '@/lib/api';

interface EventListProps {
  events: Event[];
  date: Date;
}

export default function EventList({ events, date }: EventListProps) {
  const dayEvents = events.filter(event => {
    const eventDate = new Date(event.start_time);
    return (
      eventDate.getFullYear() === date.getFullYear() &&
      eventDate.getMonth() === date.getMonth() &&
      eventDate.getDate() === date.getDate()
    );
  }).sort((a, b) => new Date(a.start_time).getTime() - new Date(b.start_time).getTime());

  return (
    <Paper elevation={0} sx={{ p: 2 }}>
      <Typography variant="h6" gutterBottom>
        Events for {format(date, 'MMMM d, yyyy')}
      </Typography>
      
      {dayEvents.length === 0 ? (
        <Typography color="text.secondary" align="center" sx={{ py: 4 }}>
          No events scheduled for this day
        </Typography>
      ) : (
        <List sx={{ width: '100%' }}>
          {dayEvents.map((event, index) => (
            <React.Fragment key={event.id}>
              <ListItem alignItems="flex-start">
                <ListItemText
                  primary={
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <Typography
                        component="span"
                        variant="body2"
                        color="text.secondary"
                        sx={{ minWidth: 100 }}
                      >
                        {format(new Date(event.start_time), 'h:mm a')}
                      </Typography>
                      <Typography component="span" variant="subtitle1">
                        {event.title}
                      </Typography>
                    </Box>
                  }
                  secondary={
                    <Box sx={{ ml: '100px' }}>
                      {event.location && (
                        <Typography component="span" variant="body2" display="block">
                          📍 {event.location}
                        </Typography>
                      )}
                      {event.participants.length > 0 && (
                        <Typography component="span" variant="body2" display="block">
                          👥 {event.participants.join(', ')}
                        </Typography>
                      )}
                      {event.description && (
                        <Typography
                          component="span"
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
              </ListItem>
              {index < dayEvents.length - 1 && <Divider component="li" />}
            </React.Fragment>
          ))}
        </List>
      )}
    </Paper>
  );
}
