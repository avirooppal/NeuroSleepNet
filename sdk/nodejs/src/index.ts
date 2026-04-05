import axios, { AxiosInstance } from "axios";

export interface MemoryMetadata {
  [key: string]: any;
}

export interface Memory {
  id: string;
  user_id: string;
  task_id?: string;
  content: string;
  metadata: MemoryMetadata;
  consolidation_score: number;
  access_count: number;
  status: string;
  created_at: string;
  last_accessed_at: string;
  last_consolidated_at?: string;
}

export interface SearchResult extends Memory {
  attention_score: number;
  why_retrieved: string;
}

export interface SearchResponse {
  memories: SearchResult[];
  sleep_last_run?: string;
  residual_context_applied: boolean;
}

export class NeuroSleepClient {
  private client: AxiosInstance;

  constructor(
    apiKey: string,
    baseUrl: string = "http://localhost:8001/api/v1"
  ) {
    this.client = axios.create({
      baseURL: baseUrl.replace(/\/$/, ""),
      headers: {
        "X-API-KEY": apiKey,
        "Content-Type": "application/json",
      },
    });
  }

  // Tasks
  async createTask(name: string) {
    const response = await this.client.post("/tasks/", { name });
    return response.data;
  }

  async listTasks() {
    const response = await this.client.get("/tasks/");
    return response.data;
  }

  // Memories
  async addMemory(content: string, taskId?: string, metadata: MemoryMetadata = {}) {
    const payload: any = { content, metadata };
    if (taskId) payload.task_id = taskId;
    const response = await this.client.post("/memories/", payload);
    return response.data;
  }

  async listMemories(taskId?: string, page: number = 1, size: number = 50) {
    const params: any = { page, size };
    if (taskId) params.task_id = taskId;
    const response = await this.client.get("/memories/", { params });
    return response.data;
  }

  // Search
  async search(query: string, taskId?: string, topK: number = 5): Promise<SearchResponse> {
    const payload: any = { query, top_k: topK };
    if (taskId) payload.task_id = taskId;
    const response = await this.client.post("/search/", payload);
    return response.data;
  }

  // Sleep
  async triggerSleep() {
    const response = await this.client.post("/sleep/trigger");
    return response.data;
  }

  async getSleepHistory() {
    const response = await this.client.get("/sleep/history");
    return response.data;
  }

  // Dashboard
  async getStats() {
    const response = await this.client.get("/dashboard/stats");
    return response.data;
  }
}
