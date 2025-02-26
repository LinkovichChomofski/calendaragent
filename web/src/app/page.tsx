'use client';

import { useState, useEffect, useRef } from 'react';
import { Box, Container, Paper, TextField, IconButton, Typography, Grid, CircularProgress, Button } from '@mui/material';
import { Send as SendIcon, Sync as SyncIcon, Add as AddIcon } from '@mui/icons-material';
import { api, Event, CommandResponse, SyncStatus, EventCreateRequest } from '@/lib/api';
import Calendar from '@/components/Calendar';
import EventList from '@/components/EventList';
import EventForm from '@/components/EventForm';

export default function Home() {
  const [command, setCommand] = useState('');
  const [events, setEvents] = useState<Event[]>([]);
  const [loading, setLoading] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [syncStatus, setSyncStatus] = useState<SyncStatus>({
    success: false,
    new_events: 0,
    updated_events: 0,
    deleted_events: 0,
    errors: []
  });
  const [selectedDate, setSelectedDate] = useState(new Date());
  const [selectedDateRange, setSelectedDateRange] = useState<'day' | 'week' | 'month'>('week');
  const [eventFormOpen, setEventFormOpen] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let reconnectTimeout: NodeJS.Timeout;
    let isConnecting = false;
    let reconnectAttempts = 0;
    const maxReconnectAttempts = 5;
    
    // Connect to WebSocket for real-time updates
    const connectWebSocket = (useFallbackPath = false) => {
      if (isConnecting || reconnectAttempts >= maxReconnectAttempts) {
        console.log('Skipping WebSocket connection attempt:', {
          isConnecting,
          reconnectAttempts,
          maxReconnectAttempts,
          useFallbackPath
        });
        return;
      }
      
      isConnecting = true;
      console.log('Starting WebSocket connection attempt...');
      
      try {
        // Close existing connection if any
        if (wsRef.current) {
          console.log('Closing existing WebSocket connection');
          wsRef.current.close();
          wsRef.current = null;
        }
        
        const wsUrl = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000';
        const path = '/ws';  // Always use /ws path
        const fullUrl = `${wsUrl}${path}`;
        console.log('Connecting to WebSocket:', fullUrl);
        
        let ws: WebSocket;
        try {
          ws = new WebSocket(fullUrl);
          wsRef.current = ws;
        } catch (err) {
          console.error('Error creating WebSocket:', err);
          isConnecting = false;
          if (reconnectAttempts < maxReconnectAttempts) {
            reconnectAttempts++;
            const delay = Math.min(1000 * Math.pow(2, reconnectAttempts), 10000);
            console.log('Planning WebSocket reconnection after connection error:', {
              attempt: reconnectAttempts,
              maxAttempts: maxReconnectAttempts,
              delayMs: delay
            });
            reconnectTimeout = setTimeout(() => connectWebSocket(useFallbackPath), delay);
          }
          return;
        }
        
        ws.onopen = () => {
          console.log('WebSocket connection opened successfully');
          isConnecting = false;
          reconnectAttempts = 0; // Reset attempts on successful connection
          
          // Send initial ping
          if (ws.readyState === WebSocket.OPEN) {
            try {
              ws.send(JSON.stringify({ type: 'ping' }));
            } catch (err) {
              console.error('Error sending initial ping:', err);
            }
          }
        };
        
        ws.onclose = (event) => {
          console.log('WebSocket connection closed:', {
            code: event.code,
            reason: event.reason,
            wasClean: event.wasClean,
            useFallbackPath
          });
          
          isConnecting = false;
          wsRef.current = null;
          
          if (reconnectAttempts < maxReconnectAttempts) {
            reconnectAttempts++;
            const delay = Math.min(1000 * Math.pow(2, reconnectAttempts), 10000);
            console.log('Planning WebSocket reconnection:', {
              attempt: reconnectAttempts,
              maxAttempts: maxReconnectAttempts,
              delayMs: delay,
              useFallbackPath
            });
            reconnectTimeout = setTimeout(() => connectWebSocket(useFallbackPath), delay);
          } else {
            console.error('Max WebSocket reconnection attempts reached');
          }
        };
        
        ws.onerror = (error) => {
          console.error('WebSocket error:', error);
          isConnecting = false;
        };
        
        ws.onmessage = (event) => {
          console.log('Received WebSocket message:', event.data);
          try {
            const data = JSON.parse(event.data);
            console.log('Parsed WebSocket message:', data);
            
            if (data.type === 'connection_established') {
              console.log('WebSocket connection established confirmation received');
            } else if (data.type === 'sync_complete') {
              console.log('Sync complete notification received:', data.data);
              // Ensure data has all the required properties
              setSyncStatus({
                success: data?.data?.success || false,
                new_events: data?.data?.new_events || 0,
                updated_events: data?.data?.updated_events || 0,
                deleted_events: data?.data?.deleted_events || 0,
                errors: data?.data?.errors || []
              });
              setSyncing(false);
              fetchEvents();
            } else if (data.type === 'pong') {
              console.log('Received pong from server');
            } else {
              console.log('Received unknown message type:', data.type);
            }
          } catch (error) {
            console.error('Error processing WebSocket message:', error);
          }
        };
      } catch (error) {
        console.error('Error creating WebSocket:', error);
        isConnecting = false;
        wsRef.current = null;
        
        if (reconnectAttempts < maxReconnectAttempts) {
          reconnectAttempts++;
          const delay = Math.min(1000 * Math.pow(2, reconnectAttempts), 10000);
          reconnectTimeout = setTimeout(() => connectWebSocket(useFallbackPath), delay);
        } else {
          console.error('Max WebSocket reconnection attempts reached after error');
        }
      }
    };

    // Start WebSocket connection
    console.log('Initializing WebSocket connection...');
    connectWebSocket(false);
    
    // Start heartbeat to keep connection alive
    console.log('Starting WebSocket heartbeat...');
    const heartbeatInterval = setInterval(() => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        console.log('Sending WebSocket heartbeat ping');
        wsRef.current.send(JSON.stringify({ type: 'ping' }));
      }
    }, 30000);

    // Fetch initial events
    console.log('Fetching initial events...');
    fetchEvents();

    return () => {
      console.log('Cleaning up WebSocket connection...');
      clearTimeout(reconnectTimeout);
      clearInterval(heartbeatInterval);
      if (wsRef.current) {
        console.log('Closing WebSocket connection during cleanup');
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, []);

  const fetchEvents = async () => {
    try {
      let data: Event[] = [];
      
      setLoading(true);
      
      try {
        switch (selectedDateRange) {
          case 'day':
            // Get events for selected day
            const startOfDay = new Date(selectedDate);
            startOfDay.setHours(0, 0, 0, 0);
            const endOfDay = new Date(selectedDate);
            endOfDay.setHours(23, 59, 59, 999);
            data = await api.getEventsForRange(startOfDay, endOfDay);
            break;
          case 'week':
            data = await api.getWeekEvents();
            break;
          case 'month':
            data = await api.getMonthEvents();
            break;
          default:
            data = await api.getWeekEvents();
        }
      } catch (apiError) {
        console.error('API error when fetching events:', apiError);
        // Set data to empty array if API call fails
        data = [];
        setError(apiError instanceof Error ? apiError.message : 'Failed to fetch events from server');
      }
      
      setEvents(data);
    } catch (err) {
      console.error('Error fetching events:', err);
      setError(err instanceof Error ? err.message : 'Failed to fetch events');
      // Set events to empty array to prevent UI from crashing
      setEvents([]);
    } finally {
      setLoading(false);
    }
  };

  const handleSync = async () => {
    setSyncing(true);
    setError(null);
    
    try {
      const data = await api.syncCalendar();
      // Ensure data has all the required properties
      setSyncStatus({
        success: data?.success || false,
        new_events: data?.new_events || 0,
        updated_events: data?.updated_events || 0,
        deleted_events: data?.deleted_events || 0,
        errors: data?.errors || []
      });
    } catch (err) {
      console.error('Error syncing calendar:', err);
      setError(err instanceof Error ? err.message : 'Sync failed');
      // Reset syncStatus to default values
      setSyncStatus({
        success: false,
        new_events: 0,
        updated_events: 0,
        deleted_events: 0,
        errors: ['Sync failed: ' + (err instanceof Error ? err.message : 'Unknown error')]
      });
      setSyncing(false);
    }
  };

  const handleCommand = async () => {
    if (!command.trim()) return;

    setLoading(true);
    setError(null);

    try {
      const data = await api.sendCommand(command);
      if (data.events) {
        setEvents(data.events);
      }
      setCommand('');
      setError(null);
    } catch (err) {
      console.error('Error processing command:', err);
      setError(err instanceof Error ? err.message : 'Command failed');
    } finally {
      setLoading(false);
    }
  };

  const handleDateRangeChange = (range: 'day' | 'week' | 'month') => {
    setSelectedDateRange(range);
    // When changing date range, we should fetch events for that range
    setTimeout(fetchEvents, 0);
  };

  const handleDeleteEvent = async (eventId: string) => {
    try {
      setLoading(true);
      const response = await api.deleteEvent(eventId);
      if (response.success) {
        // Remove the deleted event from the local state
        setEvents(events.filter(event => event.id !== eventId));
        setError(null);
      } else {
        setError(response.error || 'Failed to delete event');
      }
    } catch (err) {
      console.error('Error deleting event:', err);
      setError(err instanceof Error ? err.message : 'Failed to delete event');
    } finally {
      setLoading(false);
    }
  };

  const handleCreateEvent = async (eventData: EventCreateRequest) => {
    try {
      setLoading(true);
      const response = await api.createEvent(eventData);
      if (response.success) {
        setEventFormOpen(false);
        // Refresh the events list
        fetchEvents();
        setError(null);
      } else {
        setError(response.error || 'Failed to create event');
      }
    } catch (err) {
      console.error('Error creating event:', err);
      setError(err instanceof Error ? err.message : 'Failed to create event');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    // Fetch events whenever the selected date or date range changes
    fetchEvents();
  }, [selectedDate, selectedDateRange]);

  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      <Paper elevation={3} sx={{ p: 3, mb: 3 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
          <Typography variant="h4" component="h1" sx={{ flexGrow: 1 }}>
            Calendar Agent
          </Typography>
          
          <Box sx={{ display: 'flex', mr: 2 }}>
            <IconButton
              onClick={() => handleDateRangeChange('day')}
              color={selectedDateRange === 'day' ? 'primary' : 'default'}
              title="Day view"
            >
              <span style={{ fontSize: '0.8rem' }}>Day</span>
            </IconButton>
            <IconButton
              onClick={() => handleDateRangeChange('week')}
              color={selectedDateRange === 'week' ? 'primary' : 'default'}
              title="Week view"
            >
              <span style={{ fontSize: '0.8rem' }}>Week</span>
            </IconButton>
            <IconButton
              onClick={() => handleDateRangeChange('month')}
              color={selectedDateRange === 'month' ? 'primary' : 'default'}
              title="Month view"
            >
              <span style={{ fontSize: '0.8rem' }}>Month</span>
            </IconButton>
          </Box>
          
          <Button
            variant="contained"
            color="primary"
            startIcon={<AddIcon />}
            onClick={() => setEventFormOpen(true)}
            sx={{ mr: 2 }}
          >
            Create Event
          </Button>
          
          <IconButton
            onClick={handleSync}
            disabled={syncing}
            color="primary"
            aria-label="Sync calendar"
            title="Sync with Google Calendar"
            sx={{ mr: 1 }}
          >
            {syncing ? <CircularProgress size={24} /> : <SyncIcon />}
          </IconButton>
        </Box>

        {syncStatus && (syncStatus.new_events > 0 || syncStatus.updated_events > 0 || syncStatus.deleted_events > 0 || (syncStatus.errors && syncStatus.errors.length > 0)) && (
          <Paper variant="outlined" sx={{ p: 2, mb: 2 }}>
            <Typography variant="subtitle2" color="text.secondary" gutterBottom>
              Last Sync Results:
            </Typography>
            <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
              <Typography>
                <strong>New Events:</strong> {syncStatus.new_events || 0}
              </Typography>
              <Typography>
                <strong>Updated:</strong> {syncStatus.updated_events || 0}
              </Typography>
              <Typography>
                <strong>Deleted:</strong> {syncStatus.deleted_events || 0}
              </Typography>
            </Box>
            {syncStatus.errors && syncStatus.errors.length > 0 && (
              <Typography color="error" sx={{ mt: 1 }}>
                Errors: {syncStatus.errors.join(', ')}
              </Typography>
            )}
          </Paper>
        )}

        {error && (
          <Paper variant="outlined" sx={{ p: 2, mb: 2, bgcolor: '#fff4f4' }}>
            <Typography color="error">
              {error}
            </Typography>
          </Paper>
        )}

        <Grid container spacing={3}>
          <Grid item xs={12} md={4}>
            <Calendar
              events={events}
              selectedDate={selectedDate}
              onDateSelect={setSelectedDate}
            />
          </Grid>
          <Grid item xs={12} md={8}>
            <EventList
              events={events}
              date={selectedDate}
              dateRange={selectedDateRange}
              onDeleteEvent={handleDeleteEvent}
            />
          </Grid>
        </Grid>

        <Box sx={{ display: 'flex', gap: 1, mt: 3 }}>
          <TextField
            fullWidth
            variant="outlined"
            placeholder="Type a command (e.g., 'Show my events for today')"
            value={command}
            onChange={(e) => setCommand(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && handleCommand()}
            disabled={loading}
            inputProps={{
              'aria-label': 'Command input',
              autoComplete: 'off'
            }}
            autoComplete="off"
          />
          <IconButton
            onClick={handleCommand}
            disabled={loading || !command.trim()}
            color="primary"
            aria-label="Send command"
          >
            {loading ? <CircularProgress size={24} /> : <SendIcon />}
          </IconButton>
        </Box>
      </Paper>
      
      {/* Event Form Dialog */}
      <EventForm 
        open={eventFormOpen}
        onClose={() => setEventFormOpen(false)}
        onSubmit={handleCreateEvent}
        initialDate={selectedDate}
      />
    </Container>
  );
}
