const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

export const getToken = (): string | null => localStorage.getItem("automail_token");
export const setToken = (token: string) => localStorage.setItem("automail_token", token);
export const removeToken = () => localStorage.removeItem("automail_token");

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string>),
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  if (!(options.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }

  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers,
  });

  if (response.status === 401) {
    if (!endpoint.startsWith("/auth/")) {
      removeToken();
    }
  }

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ detail: "Request failed" }));
    let msg = "Request failed";
    if (typeof errorData.detail === "string") {
      msg = errorData.detail;
    } else if (Array.isArray(errorData.detail)) {
      msg = errorData.detail.map((e: any) => `${e.loc?.slice(-1)[0] || 'field'}: ${e.msg}`).join("; ");
    }
    throw new Error(msg);
  }

  if (response.status === 204) {
    return {} as T;
  }

  return response.json();
}

export const api = {
  // Auth
  signup: (data: any) => request<{ access_token: string }>("/auth/signup", { method: "POST", body: JSON.stringify(data) }),
  login: (data: any) => request<{ access_token: string }>("/auth/login", { method: "POST", body: JSON.stringify(data) }),
  googleAuth: (email: string) => request<{ access_token: string }>("/auth/google", { method: "POST", body: JSON.stringify({ email }) }),
  getGoogleAuthUrl: () => request<{ url: string }>("/auth/google/url"),

  // Settings
  getSettings: () => request<any>("/settings"),
  updateSettings: (data: any) => request<any>("/settings", { method: "PUT", body: JSON.stringify(data) }),

  // Resumes & Context
  uploadResume: (formData: FormData, mode: string = "keep_unique") => request<any>(`/resume/upload?mode=${mode}`, { method: "POST", body: formData }),
  listResumes: () => request<any[]>("/resume"),
  triggerParse: (id: number, mode: string = "keep_unique") => request<any>(`/resume/${id}/parse?mode=${mode}`, { method: "POST" }),

  getProfile: () => request<any>("/context/profile"),
  updateProfile: (data: any) => request<any>("/context/profile", { method: "PUT", body: JSON.stringify(data) }),

  listExperiences: () => request<any[]>("/context/experience"),
  createExperience: (data: any) => request<any>("/context/experience", { method: "POST", body: JSON.stringify(data) }),
  deleteExperience: (id: number) => request<any>(`/context/experience/${id}`, { method: "DELETE" }),

  listProjects: () => request<any[]>("/context/projects"),
  createProject: (data: any) => request<any>("/context/projects", { method: "POST", body: JSON.stringify(data) }),
  deleteProject: (id: number) => request<any>(`/context/projects/${id}`, { method: "DELETE" }),

  listAchievements: () => request<any[]>("/context/achievements"),
  createAchievement: (data: any) => request<any>("/context/achievements", { method: "POST", body: JSON.stringify(data) }),
  deleteAchievement: (id: number) => request<any>(`/context/achievements/${id}`, { method: "DELETE" }),

  // Templates
  listTemplates: () => request<any[]>("/templates"),
  createTemplate: (data: any) => request<any>("/templates", { method: "POST", body: JSON.stringify(data) }),
  updateTemplate: (id: number, data: any) => request<any>(`/templates/${id}`, { method: "PUT", body: JSON.stringify(data) }),
  deleteTemplate: (id: number) => request<any>(`/templates/${id}`, { method: "DELETE" }),

  // Contacts
  listContacts: () => request<any[]>("/contacts"),
  createContact: (data: any) => request<any>("/contacts", { method: "POST", body: JSON.stringify(data) }),
  updateContactStatus: (id: number, status: string) => request<any>(`/contacts/${id}/status`, { method: "PUT", body: JSON.stringify({ status }) }),
  deleteContact: (id: number) => request<any>(`/contacts/${id}`, { method: "DELETE" }),

  // Scrapers
  scrapeCareerPage: (url: string) => request<any>("/scrapers/career-page", { method: "POST", body: JSON.stringify({ url }) }),
  scrapeGithub: (username_or_repo: string) => request<any>("/scrapers/github", { method: "POST", body: JSON.stringify({ username_or_repo }) }),
  scrapeJobPortal: (url: string) => request<any>("/scrapers/job-portal", { method: "POST", body: JSON.stringify({ url }) }),
  scrapeLinkedin: (url: string) => request<any>("/scrapers/linkedin", { method: "POST", body: JSON.stringify({ url }) }),
  listScrapeQueue: () => request<any[]>("/scrapers/queue"),
  runNormalizer: () => request<any>("/scrapers/normalize", { method: "POST" }),

  // Send Queue & Approval
  listQueue: () => request<any[]>("/queue"),
  personalizeContact: (id: number, template_id?: number) => request<any>(`/queue/${id}/personalize${template_id ? `?template_id=${template_id}` : ""}`, { method: "POST" }),
  approveQueueItem: (id: number) => request<any>(`/queue/${id}/approve`, { method: "POST" }),
  rejectQueueItem: (id: number) => request<any>(`/queue/${id}/reject`, { method: "POST" }),
};
