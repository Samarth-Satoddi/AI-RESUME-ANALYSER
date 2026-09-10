import { apiClient } from './client';
import { User, Profile, TokenResponse } from '../types/auth';

export const authApi = {
  register: async (payload: { email: string; password: string; full_name: string }): Promise<User> => {
    const { data } = await apiClient.post<User>('/auth/register', payload);
    return data;
  },

  login: async (payload: { email: string; password: string }): Promise<TokenResponse> => {
    const { data } = await apiClient.post<TokenResponse>('/auth/login', payload);
    return data;
  },

  getMe: async (): Promise<User> => {
    const { data } = await apiClient.get<User>('/auth/me');
    return data;
  },

  getProfile: async (): Promise<Profile> => {
    const { data } = await apiClient.get<Profile>('/profile');
    return data;
  },

  updateProfile: async (payload: Partial<Profile>): Promise<Profile> => {
    const { data } = await apiClient.put<Profile>('/profile', payload);
    return data;
  },

  changePassword: async (payload: { current_password: string; new_password: string }): Promise<{ message: string }> => {
    const { data } = await apiClient.post<{ message: string }>('/auth/change-password', payload);
    return data;
  },

  logout: async (refreshToken?: string | null): Promise<void> => {
    if (refreshToken) {
      try {
        await apiClient.post('/auth/logout', { refresh_token: refreshToken });
      } catch {
        // Continue cleanup even if server is unreachable
      }
    }
  },
};
