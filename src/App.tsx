import React from 'react';
import { ServerDashboard } from './components/ServerDashboard';
import rawInventoryData from '../inventario_amt.json';
import { RawSharePointItem } from './types/inventory';

export const App: React.FC = () => {
  return (
    <ServerDashboard rawInventory={rawInventoryData as RawSharePointItem[]} />
  );
};

export default App;
