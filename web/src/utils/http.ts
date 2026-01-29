import { Authorization } from '@/constants/authorization';
import { getAuthorization } from '@/utils/authorization-util';
import { message } from 'antd';

interface HttpOptions {
  headers?: Record<string, string>;
  timeout?: number;
}

interface HttpResponse<T = any> {
  code: number;
  data?: T;
  message: string;
}

class Http {
  private baseURL: string = '';

  private async request<T>(
    url: string,
    options: RequestInit,
  ): Promise<HttpResponse<T>> {
    try {
      const response = await fetch(`${this.baseURL}${url}`, {
        ...options,
        headers: {
          'Content-Type': 'application/json',
          [Authorization]: getAuthorization(),
          ...options.headers,
        },
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      return data;
    } catch (error) {
      console.error('Request failed:', error);
      message.error('网络请求失败，请稍后重试');
      throw error;
    }
  }

  get<T>(url: string, options?: HttpOptions): Promise<HttpResponse<T>> {
    return this.request<T>(url, {
      method: 'GET',
      headers: options?.headers,
    });
  }

  post<T>(
    url: string,
    data?: any,
    options?: HttpOptions,
  ): Promise<HttpResponse<T>> {
    return this.request<T>(url, {
      method: 'POST',
      body: JSON.stringify(data),
      headers: options?.headers,
    });
  }

  put<T>(
    url: string,
    data?: any,
    options?: HttpOptions,
  ): Promise<HttpResponse<T>> {
    return this.request<T>(url, {
      method: 'PUT',
      body: JSON.stringify(data),
      headers: options?.headers,
    });
  }

  delete<T>(url: string, options?: HttpOptions): Promise<HttpResponse<T>> {
    return this.request<T>(url, {
      method: 'DELETE',
      headers: options?.headers,
    });
  }
}

export const http = new Http();
