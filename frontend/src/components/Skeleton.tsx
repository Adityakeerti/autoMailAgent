import React from 'react';

interface SkeletonProps {
  width?: string;
  height?: string;
  borderRadius?: string;
  className?: string;
  style?: React.CSSProperties;
}

export const Skeleton: React.FC<SkeletonProps> = ({
  width = '100%',
  height = '16px',
  borderRadius = '4px',
  className = '',
  style = {}
}) => {
  return (
    <div
      className={`skeleton-pulse ${className}`}
      style={{
        width,
        height,
        borderRadius,
        ...style
      }}
    />
  );
};

export const SkeletonStatCard: React.FC = () => {
  return (
    <div className="stat-card">
      <Skeleton width="60%" height="12px" style={{ marginBottom: '12px' }} />
      <Skeleton width="40%" height="28px" style={{ marginBottom: '8px' }} />
      <Skeleton width="80%" height="12px" />
    </div>
  );
};

export const SkeletonTableRow: React.FC<{ columns?: number }> = ({ columns = 4 }) => {
  return (
    <tr>
      {Array.from({ length: columns }).map((_, i) => (
        <td key={i}>
          <Skeleton width={i === 0 ? '70%' : i === columns - 1 ? '40%' : '50%'} height="14px" />
        </td>
      ))}
    </tr>
  );
};

export const SkeletonTable: React.FC<{ rows?: number; columns?: number }> = ({ rows = 5, columns = 4 }) => {
  return (
    <div className="table-container">
      <table className="table">
        <thead>
          <tr>
            {Array.from({ length: columns }).map((_, i) => (
              <th key={i}>
                <Skeleton width="60%" height="12px" />
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {Array.from({ length: rows }).map((_, i) => (
            <SkeletonTableRow key={i} columns={columns} />
          ))}
        </tbody>
      </table>
    </div>
  );
};

export const SkeletonCard: React.FC<{ height?: string }> = ({ height = '140px' }) => {
  return (
    <div className="card">
      <div className="card-header" style={{ marginBottom: '16px' }}>
        <Skeleton width="30%" height="18px" />
        <Skeleton width="15%" height="24px" borderRadius="4px" />
      </div>
      <Skeleton width="100%" height={height} borderRadius="6px" />
    </div>
  );
};

export const TopLoadingBar: React.FC<{ active: boolean }> = ({ active }) => {
  if (!active) return null;
  return (
    <div className="top-loading-bar-container">
      <div className="top-loading-bar-progress" />
    </div>
  );
};
