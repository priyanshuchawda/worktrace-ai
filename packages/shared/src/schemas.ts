import { z } from "zod";

const NonEmptyStringSchema = z.string().trim().min(1);
const IsoDateTimeSchema = z.iso.datetime({ offset: true });
const ConfidenceSchema = z.number().min(0).max(1);
const EvidenceEventIdsSchema = z.array(NonEmptyStringSchema).min(1);

export const PrivacyLevelSchema = z.enum(["safe", "sensitive", "secret", "redacted", "unknown"]);

export const SessionStatusSchema = z.enum(["recording", "paused", "stopped", "interrupted"]);

export const FindingSeveritySchema = z.enum(["low", "medium", "high"]);

export const AiReportProviderSchema = z.enum(["local_ollama", "gemini_gemma_dev"]);

export const ModelRunMetadataSchema = z.object({
  model_name: NonEmptyStringSchema,
  model_version: NonEmptyStringSchema.optional(),
  provider: AiReportProviderSchema.optional(),
  requested_model: NonEmptyStringSchema.optional(),
  actual_model: NonEmptyStringSchema.optional(),
  fallback_used: z.boolean().optional(),
  prompt_version: NonEmptyStringSchema.optional(),
  input_hash: NonEmptyStringSchema.optional(),
  generated_at: IsoDateTimeSchema
});

export const EventSchema = z.object({
  id: NonEmptyStringSchema,
  session_id: NonEmptyStringSchema,
  timestamp: IsoDateTimeSchema,
  source: NonEmptyStringSchema,
  type: NonEmptyStringSchema,
  privacy_level: PrivacyLevelSchema,
  confidence: ConfidenceSchema,
  metadata: z.record(z.string(), z.unknown()).default({})
});

export const SessionSchema = z.object({
  id: NonEmptyStringSchema,
  started_at: IsoDateTimeSchema,
  ended_at: IsoDateTimeSchema.nullish(),
  status: SessionStatusSchema,
  title: NonEmptyStringSchema.optional(),
  goal: NonEmptyStringSchema.optional(),
  project_label: NonEmptyStringSchema.optional(),
  tags: z.array(NonEmptyStringSchema).default([]),
  storage_path: NonEmptyStringSchema.optional(),
  privacy_mode: NonEmptyStringSchema
});

export const TimelineChunkSchema = z.object({
  id: NonEmptyStringSchema,
  session_id: NonEmptyStringSchema,
  start: IsoDateTimeSchema,
  end: IsoDateTimeSchema,
  label: NonEmptyStringSchema,
  summary: NonEmptyStringSchema,
  evidence_event_ids: EvidenceEventIdsSchema,
  confidence: ConfidenceSchema
});

export const FindingSchema = z.object({
  id: NonEmptyStringSchema,
  session_id: NonEmptyStringSchema,
  type: NonEmptyStringSchema,
  title: NonEmptyStringSchema,
  description: NonEmptyStringSchema,
  evidence_event_ids: EvidenceEventIdsSchema,
  severity: FindingSeveritySchema,
  confidence: ConfidenceSchema
});

const EvidenceBackedTextSchema = z.object({
  title: NonEmptyStringSchema.optional(),
  text: NonEmptyStringSchema.optional(),
  path: NonEmptyStringSchema.optional(),
  command: NonEmptyStringSchema.optional(),
  evidence_event_ids: EvidenceEventIdsSchema
});

export const ReportSchema = z.object({
  session_id: NonEmptyStringSchema,
  session_title: NonEmptyStringSchema,
  summary: NonEmptyStringSchema,
  observed_work: z.array(EvidenceBackedTextSchema).default([]),
  timeline: z.array(TimelineChunkSchema),
  blockers: z.array(FindingSchema),
  context_switches: z.array(EvidenceBackedTextSchema).default([]),
  unfinished_work: z.array(EvidenceBackedTextSchema).default([]),
  repeated_actions: z.array(FindingSchema),
  important_files: z.array(EvidenceBackedTextSchema),
  commands: z.array(EvidenceBackedTextSchema),
  workflow_steps: z.array(EvidenceBackedTextSchema),
  continuation_notes: z.array(EvidenceBackedTextSchema).default([]),
  confidence: ConfidenceSchema,
  model_metadata: ModelRunMetadataSchema.optional()
});
