'use client';

import { useState, useEffect, useRef } from 'react';
import { Box, Container, Paper, TextField, IconButton, Typography, Grid, CircularProgress } from '@mui/material';
import { Send as SendIcon, Sync as SyncIcon } from '@mui/icons-material';
import { api, Event, CommandResponse, SyncStatus } from '@/lib/api';
import Calendar from '@/components/Calendar';
import EventList from '@/components/EventList';

export default function Home() {
  const [command, setCommand] = useState('');
  const [events, setEvents] = useState<Event[]>([]);
  const [loading, setLoading] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [syncStatus, setSyncStatus] = useState<SyncStatus | null>(null);
  const [selectedDate, setSelectedDate] = useState(new Date());
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
        
        const ws = new WebSocket(fullUrl);
        wsRef.current = ws;
        
        ws.onopen = () => {
          console.log('WebSocket connection opened successfully');
          isConnecting = false;
          reconnectAttempts = 0; // Reset attempts on successful connection
          
          // Send initial ping
          if (ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ type: 'ping' }));
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
              console.log('Sync complete notification received:', data.stats);
              setSyncStatus(data.stats);
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
      const data = await api.getWeekEvents();
      setEvents(data);
      setError(null);
    } catch (err) {
      console.error('Error fetching events:', err);
      setError(err instanceof Error ? err.message : 'Failed to fetch events');
    }
  };

  const handleSync = async () => {
    setSyncing(true);
    setError(null);
    
    try {
      const data = await api.syncCalendar();
      setSyncStatus(data);
    } catch (err) {
      console.error('Error syncing calendar:', err);
      setError(err instanceof Error ? err.message : 'Sync failed');
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

  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      <Paper elevation={3} sx={{ p: 3, mb: 3 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
          <Typography variant="h4" component="h1" sx={{ flexGrow: 1 }}>
            Calendar Agent
          </Typography>
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

        {syncStatus && (
          <Paper variant="outlined" sx={{ p: 2, mb: 2 }}>
            <Typography variant="subtitle2" color="text.secondary" gutterBottom>
              Last Sync Results:
            </Typography>
            <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
              <Typography>
                <strong>New Events:</strong> {syncStatus.new_events}
              </Typography>
              <Typography>
                <strong>Updated:</strong> {syncStatus.updated_events}
              </Typography>
              <Typography>
                <strong>Deleted:</strong> {syncStatus.deleted_events}
              </Typography>
            </Box>
            {syncStatus.errors.length > 0 && (
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
              autoComplete: 'off',
              'data-form-type': 'other',
              'data-dashlane-label': 'command'
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
    </Container>
  );
}
