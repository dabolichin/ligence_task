import React, { useState, useEffect } from "react";
import axios from "axios";

const VerificationStats = () => {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadStats();
  }, []);

  const loadStats = async () => {
    setLoading(true);
    try {
      const response = await axios.get(
        "http://localhost:8002/api/verification/statistics",
      );
      setStats(response.data);
    } catch (error) {
      console.error("Error loading verification statistics:", error);
      setStats(null);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="space-y-4">
        <div className="animate-pulse">
          <div className="h-4 bg-gray-200 rounded w-3/4 mb-2"></div>
          <div className="h-4 bg-gray-200 rounded w-1/2 mb-2"></div>
          <div className="h-4 bg-gray-200 rounded w-2/3"></div>
        </div>
      </div>
    );
  }

  if (!stats) {
    return (
      <div className="text-center text-gray-500 py-4">
        <p>Unable to load statistics</p>
        <button
          onClick={loadStats}
          className="mt-2 text-blue-600 hover:text-blue-700 text-sm"
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 gap-3">
        <div className="bg-green-50 p-3 rounded">
          <div className="text-lg font-semibold text-green-700">
            {stats.total_verifications || 0}
          </div>
          <div className="text-sm text-green-600">Total Verifications</div>
        </div>

        <div className="bg-blue-50 p-3 rounded">
          <div className="text-lg font-semibold text-blue-700">
            {stats.successful_verifications || 0}
          </div>
          <div className="text-sm text-blue-600">Successful</div>
        </div>

        <div className="bg-red-50 p-3 rounded">
          <div className="text-lg font-semibold text-red-700">
            {stats.failed_verifications || 0}
          </div>
          <div className="text-sm text-red-600">Failed</div>
        </div>

        <div className="bg-yellow-50 p-3 rounded">
          <div className="text-lg font-semibold text-yellow-700">
            {stats.pending_verifications || 0}
          </div>
          <div className="text-sm text-yellow-600">Pending</div>
        </div>
      </div>

      {stats.success_rate !== undefined && (
        <div className="pt-3 border-t">
          <div className="text-sm text-gray-600">Success Rate</div>
          <div className="text-lg font-semibold text-green-700">
            {stats.success_rate.toFixed(1)}%
          </div>
        </div>
      )}
    </div>
  );
};

export default VerificationStats;
