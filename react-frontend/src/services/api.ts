// services/api.ts - Updated with email settings functionality
import axios from 'axios';
import { Tender, Page, Keyword, SystemStatus } from '../types';

// Base URL for API endpoints
const API_BASE_URL = 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
});

// Add email settings types
export interface EmailNotificationSettings {
  esg_emails: string[];
  credit_rating_emails: string[];
  notification_preferences: {
    send_for_new_tenders: boolean;
    send_daily_summary: boolean;
    send_urgent_notifications: boolean;
  };
}

export interface EmailSettingsResponse {
  success: boolean;
  message: string;
  settings: EmailNotificationSettings;
}

export interface TestEmailRequest {
  email: string;
  category: 'esg' | 'credit_rating';
}

export const apiRequest = async (endpoint: string, method: 'get' | 'post' = 'get', data?: any, options: any = {}) => {
  try {
    let response;
    if (method === 'get') {
      response = await api.get(endpoint, options);
    } else if (method === 'post') {
      response = await api.post(endpoint, data, options);
    }
    return response?.data;
  } catch (error) {
    console.error(`API request failed for ${endpoint}:`, error);
    throw error;
  }
};

export const apiService = {
  // System
  checkHealth: async (): Promise<SystemStatus> => {
    const data = await apiRequest('/health');
    return data as SystemStatus;
  },
  
  getSystemStatus: async (): Promise<any> => {
    const data = await apiRequest('/api/v1/system/status');
    return data;
  },
    
  triggerExtraction: async (): Promise<{ message: string }> => {
    const data = await apiRequest('/trigger-extraction', 'post');
    return data as { message: string };
  },

  // Tenders
  getTenders: async (): Promise<Tender[]> => {
    const data = await apiRequest('/api/v1/tenders/');
    return data as Tender[];
  },

  // Get detailed tender information
  getTenderDetails: async (tenderId: number): Promise<Tender> => {
    const data = await apiRequest(`/api/v1/tenders/${tenderId}`);
    return data as Tender;
  },

  // Pages
  getPages: async (): Promise<Page[]> => {
    const data = await apiRequest('/api/v1/pages/');
    return data as Page[];
  },

  createPage: async (data: { url: string; name: string }): Promise<Page> => {
    const responseData = await apiRequest('/api/v1/pages/', 'post', data);
    return responseData as Page;
  },

  updatePage: async (id: number, data: Partial<Page>): Promise<Page> => {
    const response = await api.put(`/api/v1/pages/${id}`, data);
    return response.data as Page;
  },

  deletePage: async (id: number): Promise<void> => {
    await api.delete(`/api/v1/pages/${id}`);
  },

  // Keywords
  getKeywords: async (): Promise<Keyword[]> => {
    const data = await apiRequest('/api/v1/keywords/');
    return data as Keyword[];
  },

  createKeyword: async (data: { keyword: string; category: 'esg' | 'credit_rating' }): Promise<Keyword> => {
    const responseData = await apiRequest('/api/v1/keywords/', 'post', data);
    return responseData as Keyword;
  },

  updateKeyword: async (id: number, data: Partial<Keyword>): Promise<Keyword> => {
    const response = await api.put(`/api/v1/keywords/${id}`, data);
    return response.data as Keyword;
  },

  deleteKeyword: async (id: number): Promise<void> => {
    await api.delete(`/api/v1/keywords/${id}`);
  },

  // Email Settings - NEW METHODS
  getEmailSettings: async (): Promise<EmailSettingsResponse> => {
    try {
      const data = await apiRequest('/api/v1/system/email-settings');
      return data as EmailSettingsResponse;
    } catch (error) {
      // Fallback to default settings if API call fails
      console.warn('Failed to load email settings from API, using defaults:', error);
      return {
        success: true,
        message: 'Using default settings',
        settings: {
          esg_emails: [],
          credit_rating_emails: [],
          notification_preferences: {
            send_for_new_tenders: true,
            send_daily_summary: true,
            send_urgent_notifications: true,
          }
        }
      };
    }
  },

  saveEmailSettings: async (settings: EmailNotificationSettings): Promise<EmailSettingsResponse> => {
    try {
      const data = await apiRequest('/api/v1/system/email-settings', 'post', settings);
      return data as EmailSettingsResponse;
    } catch (error) {
      console.error('Failed to save email settings:', error);
      return {
        success: false,
        message: 'Failed to save email settings',
        settings: settings
      };
    }
  },

  sendTestEmail: async (request: TestEmailRequest): Promise<{ success: boolean; message: string; details?: string }> => {
    try {
      const data = await apiRequest('/api/v1/system/test-email', 'post', request);
      return data as { success: boolean; message: string; details?: string };
    } catch (error) {
      console.error('Failed to send test email:', error);
      return {
        success: false,
        message: 'Failed to send test email. Please check your email configuration.',
        details: error instanceof Error ? error.message : 'Unknown error'
      };
    }
  },

  addEmailToCategory: async (category: 'esg' | 'credit_rating', email: string): Promise<{ success: boolean; message: string }> => {
    try {
      const data = await apiRequest(`/api/v1/system/email-settings/${category}/add`, 'post', { email });
      return data as { success: boolean; message: string };
    } catch (error) {
      console.error('Failed to add email:', error);
      return {
        success: false,
        message: 'Failed to add email'
      };
    }
  },

  removeEmailFromCategory: async (category: 'esg' | 'credit_rating', email: string): Promise<{ success: boolean; message: string }> => {
    try {
      const response = await api.delete(`/api/v1/system/email-settings/${category}/${encodeURIComponent(email)}`);
      return response.data as { success: boolean; message: string };
    } catch (error) {
      console.error('Failed to remove email:', error);
      return {
        success: false,
        message: 'Failed to remove email'
      };
    }
  },
};