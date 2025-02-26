import { useState, useEffect } from 'react';
import { 
  Box, 
  Button, 
  TextField, 
  Dialog, 
  DialogActions, 
  DialogContent, 
  DialogTitle,
  InputAdornment,
  IconButton
} from '@mui/material';
import { Close as CloseIcon } from '@mui/icons-material';
import { DateTimePicker } from '@mui/x-date-pickers/DateTimePicker';
import { LocalizationProvider } from '@mui/x-date-pickers/LocalizationProvider';
import { AdapterDateFns } from '@mui/x-date-pickers/AdapterDateFns';
import { EventCreateRequest } from '@/lib/api';

interface EventFormProps {
  open: boolean;
  onClose: () => void;
  onSubmit: (data: EventCreateRequest) => void;
  initialDate?: Date;
}

export default function EventForm({ open, onClose, onSubmit, initialDate = new Date() }: EventFormProps) {
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [location, setLocation] = useState('');
  const [startDate, setStartDate] = useState<Date | null>(initialDate);
  const [endDate, setEndDate] = useState<Date | null>(
    new Date(initialDate.getTime() + 60 * 60 * 1000) // Default to 1 hour after start
  );
  const [participants, setParticipants] = useState('');
  const [errors, setErrors] = useState<Record<string, string>>({});

  useEffect(() => {
    if (open) {
      // Reset form when dialog opens
      setTitle('');
      setDescription('');
      setLocation('');
      setStartDate(initialDate);
      setEndDate(new Date(initialDate.getTime() + 60 * 60 * 1000));
      setParticipants('');
      setErrors({});
    }
  }, [open, initialDate]);

  const validate = (): boolean => {
    const newErrors: Record<string, string> = {};

    if (!title.trim()) {
      newErrors.title = 'Title is required';
    }

    if (!startDate) {
      newErrors.startDate = 'Start date is required';
    }

    if (!endDate) {
      newErrors.endDate = 'End date is required';
    } else if (startDate && endDate && endDate < startDate) {
      newErrors.endDate = 'End date must be after start date';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = () => {
    if (!validate()) return;

    const eventData: EventCreateRequest = {
      title,
      description: description || undefined,
      start: startDate!.toISOString(),
      end: endDate!.toISOString(),
      location: location || undefined,
      participants: participants ? participants.split(',').map(p => p.trim()) : undefined,
      calendar_id: 'primary' // Default to primary calendar
    };

    onSubmit(eventData);
  };

  return (
    <LocalizationProvider dateAdapter={AdapterDateFns}>
      <Dialog 
        open={open} 
        onClose={onClose} 
        PaperProps={{
          sx: { width: '100%', maxWidth: 500 }
        }}
      >
        <DialogTitle sx={{ 
          display: 'flex', 
          justifyContent: 'space-between', 
          alignItems: 'center'
        }}>
          Create New Event
          <IconButton onClick={onClose} size="small">
            <CloseIcon />
          </IconButton>
        </DialogTitle>
        <DialogContent>
          <Box component="form" noValidate sx={{ mt: 1 }}>
            <TextField
              margin="normal"
              required
              fullWidth
              id="title"
              label="Event Title"
              name="title"
              autoFocus
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              error={!!errors.title}
              helperText={errors.title}
            />
            
            <TextField
              margin="normal"
              fullWidth
              id="description"
              label="Description"
              name="description"
              multiline
              rows={3}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
            />
            
            <Box sx={{ mt: 2, mb: 1 }}>
              <DateTimePicker
                label="Start Date & Time"
                value={startDate}
                onChange={(newValue) => setStartDate(newValue)}
                slotProps={{
                  textField: {
                    fullWidth: true,
                    margin: 'normal',
                    error: !!errors.startDate,
                    helperText: errors.startDate
                  }
                }}
              />
            </Box>
            
            <Box sx={{ mt: 1, mb: 1 }}>
              <DateTimePicker
                label="End Date & Time"
                value={endDate}
                onChange={(newValue) => setEndDate(newValue)}
                slotProps={{
                  textField: {
                    fullWidth: true,
                    margin: 'normal',
                    error: !!errors.endDate,
                    helperText: errors.endDate
                  }
                }}
              />
            </Box>
            
            <TextField
              margin="normal"
              fullWidth
              id="location"
              label="Location"
              name="location"
              value={location}
              onChange={(e) => setLocation(e.target.value)}
            />
            
            <TextField
              margin="normal"
              fullWidth
              id="participants"
              label="Participants"
              name="participants"
              placeholder="Comma-separated email addresses"
              value={participants}
              onChange={(e) => setParticipants(e.target.value)}
              InputProps={{
                startAdornment: participants ? (
                  <InputAdornment position="start">👥</InputAdornment>
                ) : null,
              }}
            />
          </Box>
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 3 }}>
          <Button onClick={onClose}>Cancel</Button>
          <Button 
            onClick={handleSubmit} 
            variant="contained" 
            color="primary"
          >
            Create Event
          </Button>
        </DialogActions>
      </Dialog>
    </LocalizationProvider>
  );
}
