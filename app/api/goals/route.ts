import { NextResponse } from "next/server";
import {
  CURRENT_GOALS,
  TARGET_GOALS,
  GOALS_REMAINING,
  ESTIMATED_DATE,
  LAST_UPDATED,
  CLUB_STATS,
  GOALS_PER_DAY,
} from "@/lib/goals";

export async function GET() {
  return NextResponse.json({
    currentGoals: CURRENT_GOALS,
    targetGoals: TARGET_GOALS,
    goalsRemaining: GOALS_REMAINING,
    estimatedDate: ESTIMATED_DATE.toISOString(),
    lastUpdated: LAST_UPDATED,
    goalsPerDay: GOALS_PER_DAY,
    clubStats: CLUB_STATS.map((c) => ({
      club: c.club,
      goals: c.goals,
      appearances: c.appearances,
    })),
  });
}
