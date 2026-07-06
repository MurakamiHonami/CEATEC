import { render, screen } from '@testing-library/react';
import App from './App';

test('renders current hero controls', () => {
  render(<App />);
  expect(screen.getByText(/system status: active/i)).toBeInTheDocument();
  expect(screen.getByRole('button', { name: /start system/i })).toBeInTheDocument();
});
