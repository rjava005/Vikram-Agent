import { describe, expect, it } from "vitest";
import {
	aiPolicySchema,
	citationSchema,
	feedbackStatusSchema,
	problemSchema,
} from "./index";

describe("API v1 contracts", () => {
	it("requires explicit learning feedback values", () => {
		expect(feedbackStatusSchema.options).toEqual([
			"understood",
			"unclear",
			"review_later",
		]);
		expect(feedbackStatusSchema.safeParse("confused_forever").success).toBe(
			false,
		);
	});

	it("rejects prose-only citations", () => {
		expect(citationSchema.safeParse({ excerpt: "page 1" }).success).toBe(false);
	});

	it("requires versioned project consent and classified failures", () => {
		expect(
			aiPolicySchema.safeParse({
				project_id: "123e4567-e89b-42d3-a456-426614174000",
				mode: "nebius",
				zdr_attested: true,
				revision: 1,
				updated_at: "2026-08-14T00:00:00Z",
			}).success,
		).toBe(true);
		expect(
			problemSchema.safeParse({
				type: "https://vikram.local/problems/provider-timeout",
				title: "Provider timed out",
				status: 504,
				detail: "The configured provider did not respond in time.",
				code: "provider_timeout",
				retryable: true,
			}).success,
		).toBe(true);
	});
});
