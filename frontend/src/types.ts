export type Application = {
  id: number;
  vendor: string;
  subject: string;
  job_title: string | null;
  company: string | null;
  location: string | null;
  status: string | null;
  requisition_id: string | null;
  applied_at: string | null;
  email_received_at: string;
};

export type ImportMessage = {
  provider_id: string;
  sender: string;
  subject: string;
  received_at: string | null;
  vendor: string | null;
};
