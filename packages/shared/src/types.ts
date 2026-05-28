import type { z } from "zod";
import type {
  AiReportProviderSchema,
  EventSchema,
  FindingSchema,
  FindingSeveritySchema,
  ModelRunMetadataSchema,
  PrivacyLevelSchema,
  ReportSchema,
  SessionSchema,
  SessionStatusSchema,
  TimelineChunkSchema
} from "./schemas";

export type AiReportProvider = z.infer<typeof AiReportProviderSchema>;
export type PrivacyLevel = z.infer<typeof PrivacyLevelSchema>;
export type SessionStatus = z.infer<typeof SessionStatusSchema>;
export type FindingSeverity = z.infer<typeof FindingSeveritySchema>;
export type ModelRunMetadata = z.infer<typeof ModelRunMetadataSchema>;
export type Event = z.infer<typeof EventSchema>;
export type Session = z.infer<typeof SessionSchema>;
export type TimelineChunk = z.infer<typeof TimelineChunkSchema>;
export type Finding = z.infer<typeof FindingSchema>;
export type Report = z.infer<typeof ReportSchema>;
