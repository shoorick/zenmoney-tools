#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Match transactions from ZenMoney CSV with Credo bank JSON.
"""

import argparse
import csv
import json
import sys
import pandas as pd
import datetime
from typing import List, Dict, Any, Optional, Tuple


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Match transactions from ZenMoney CSV with Credo bank JSON."
    )
    parser.add_argument(
        "zen_csv", help="Path to ZenMoney CSV file"
    )
    parser.add_argument(
        "credo_json", help="Path to Credo bank JSON file"
    )
    parser.add_argument(
        "-o", "--output", help="Output CSV file (default: stdout)", default=None
    )
    parser.add_argument(
        "-t", "--transfers", 
        help="Output CSV file for currency transfers (default: none)", 
        default=None
    )
    parser.add_argument(
        "-d", "--date-format", 
        help="Date format in ZenMoney CSV (default: %%Y-%%m-%%d)", 
        default="%Y-%m-%d"
    )
    parser.add_argument(
        "--tolerance", 
        help="Tolerance for date matching in days (default: 1)", 
        type=int, default=1
    )
    parser.add_argument(
        "-a", "--amount-tolerance", 
        help="Tolerance for amount matching in percentage (default: 0.01)", 
        type=float, default=0.01
    )
    parser.add_argument(
        "-v", "--verbose", help="Verbose output", action="store_true"
    )
    parser.add_argument(
        "--header-row", 
        help="Row number (0-based) containing headers in ZenMoney CSV (default: auto-detect)", 
        type=int, default=None
    )
    
    return parser.parse_args()


def find_header_row(file_path: str) -> int:
    """
    Find the row containing headers in a CSV file.
    
    Args:
        file_path: Path to CSV file
        
    Returns:
        Row number (0-based) containing headers
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Look for a line that contains typical ZenMoney header fields
    header_indicators = ['date', 'category', 'payee', 'comment', 'outcome', 'income']
    
    for i, line in enumerate(lines):
        line_lower = line.lower()
        # Check if at least 3 of the indicators are in the line
        if sum(1 for indicator in header_indicators if indicator in line_lower) >= 3:
            return i
    
    # If no header row found, assume it's the first row
    return 0


def load_zen_csv(file_path: str, date_format: str, header_row: Optional[int] = None) -> pd.DataFrame:
    """
    Load ZenMoney CSV file.
    
    Args:
        file_path: Path to ZenMoney CSV file
        date_format: Date format in ZenMoney CSV
        header_row: Row number (0-based) containing headers, or None to auto-detect
        
    Returns:
        DataFrame with ZenMoney transactions
    """
    try:
        # Auto-detect header row if not specified
        if header_row is None:
            header_row = find_header_row(file_path)
            
        # Try to detect encoding and delimiter automatically
        # First read the file with a specific header row
        for delimiter in [',', ';', '\t']:
            try:
                df = pd.read_csv(file_path, encoding='utf-8', delimiter=delimiter, 
                                header=header_row, skiprows=lambda x: x < header_row)
                if len(df.columns) > 1:
                    break
            except Exception:
                continue
        
        # Convert date columns to datetime
        date_columns = [col for col in df.columns if 'date' in col.lower()]
        for col in date_columns:
            # Handle comma as decimal separator in numbers that might be in date columns
            if df[col].dtype == object:  # Only process string columns
                df[col] = df[col].astype(str).str.replace(',', '.')
            
            # Try to convert to datetime
            df[col] = pd.to_datetime(df[col], format=date_format, errors='coerce')
            
        # Handle comma as decimal separator in numeric columns
        numeric_columns = [col for col in df.columns if 'amount' in col.lower() or 
                          'outcome' in col.lower() or 'income' in col.lower() or 
                          'sum' in col.lower()]
        
        for col in numeric_columns:
            if df[col].dtype == object:  # Only process string columns
                df[col] = df[col].astype(str).str.replace(',', '.').astype(float, errors='ignore')
            
        return df
    
    except Exception as e:
        print(f"Error loading ZenMoney CSV: {e}", file=sys.stderr)
        sys.exit(1)


def load_credo_json(file_path: str) -> pd.DataFrame:
    """
    Load Credo bank JSON file.
    
    Args:
        file_path: Path to Credo bank JSON file
        
    Returns:
        DataFrame with Credo bank transactions
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        df = pd.DataFrame(data)
        
        # Convert operationDateTime to datetime
        df['operationDateTime'] = pd.to_datetime(df['operationDateTime'], errors='coerce')
        
        # Create amount column (positive for credit, negative for debit)
        df['amount'] = df['credit'].fillna(0) - df['debit'].fillna(0)
        
        return df
    
    except Exception as e:
        print(f"Error loading Credo JSON: {e}", file=sys.stderr)
        sys.exit(1)


def find_currency_transfers(credo_df: pd.DataFrame, verbose: bool = False) -> pd.DataFrame:
    """
    Find pairs of transactions that represent currency transfers within the same account.
    
    Args:
        credo_df: DataFrame with Credo bank transactions
        verbose: Verbose output
        
    Returns:
        DataFrame with currency transfer pairs
    """
    # Filter transactions with "Currency exchange" description
    currency_exchanges = credo_df[credo_df['description'] == 'Currency exchange'].copy()
    
    if len(currency_exchanges) == 0:
        if verbose:
            print("No currency exchange transactions found", file=sys.stderr)
        return pd.DataFrame()
    
    # Group by account number and operation date time
    grouped = currency_exchanges.groupby(['accountNumber', 'operationDateTime'])
    
    # Find groups with exactly 2 transactions (debit and credit)
    transfer_pairs = []
    
    for (account, op_time), group in grouped:
        if len(group) == 2:
            # Check if one is debit and one is credit
            debit_tx = group[group['debit'].notnull()]
            credit_tx = group[group['credit'].notnull()]
            
            if len(debit_tx) == 1 and len(credit_tx) == 1:
                debit_row = debit_tx.iloc[0]
                credit_row = credit_tx.iloc[0]
                
                # Create a row for the transfer pair
                transfer_pair = {
                    'account_number': account,
                    'operation_date_time': op_time,
                    'from_currency': debit_row['currency'],
                    'to_currency': credit_row['currency'],
                    'from_amount': debit_row['debit'],
                    'to_amount': credit_row['credit'],
                    'from_transaction_id': debit_row['transactionId'],
                    'to_transaction_id': credit_row['transactionId'],
                    'from_stmt_entry_id': debit_row['stmtEntryId'],
                    'to_stmt_entry_id': credit_row['stmtEntryId'],
                    'exchange_rate': credit_row['credit'] / debit_row['debit'],
                    'from_amount_equivalent': debit_row['amountEquivalent'],
                    'to_amount_equivalent': credit_row['amountEquivalent']
                }
                
                transfer_pairs.append(transfer_pair)
    
    if not transfer_pairs:
        if verbose:
            print("No currency transfer pairs found", file=sys.stderr)
        return pd.DataFrame()
    
    transfers_df = pd.DataFrame(transfer_pairs)
    
    if verbose:
        print(f"Found {len(transfers_df)} currency transfer pairs", file=sys.stderr)
    
    return transfers_df


def match_transactions(
    zen_df: pd.DataFrame, 
    credo_df: pd.DataFrame, 
    transfers_df: pd.DataFrame,
    date_tolerance: int = 1, 
    amount_tolerance: float = 0.01,
    verbose: bool = False
) -> pd.DataFrame:
    """
    Match transactions from ZenMoney CSV with Credo bank JSON.
    
    Args:
        zen_df: DataFrame with ZenMoney transactions
        credo_df: DataFrame with Credo bank transactions
        transfers_df: DataFrame with currency transfer pairs
        date_tolerance: Tolerance for date matching in days
        amount_tolerance: Tolerance for amount matching in percentage
        verbose: Verbose output
        
    Returns:
        DataFrame with matched transactions
    """
    # Identify date columns in zen_df
    date_columns = [col for col in zen_df.columns if 'date' in col.lower()]
    if not date_columns:
        print("No date columns found in ZenMoney CSV", file=sys.stderr)
        sys.exit(1)
    
    # Identify amount columns in zen_df
    amount_columns = []
    
    # First check for income columns
    income_columns = [col for col in zen_df.columns if 'income' in col.lower() and 'currency' not in col.lower()]
    if income_columns:
        amount_columns.extend(income_columns)
    
    # Then check for outcome columns
    outcome_columns = [col for col in zen_df.columns if 'outcome' in col.lower() and 'currency' not in col.lower()]
    if outcome_columns:
        amount_columns.extend(outcome_columns)
    
    # Finally check for generic amount columns
    if not amount_columns:
        amount_columns = [col for col in zen_df.columns if 'amount' in col.lower() or 'sum' in col.lower()]
    
    if not amount_columns:
        print("No amount columns found in ZenMoney CSV", file=sys.stderr)
        sys.exit(1)
    
    # Create a new DataFrame for results
    result = []
    
    # For each ZenMoney transaction
    for _, zen_row in zen_df.iterrows():
        zen_date = zen_row[date_columns[0]]
        
        # Skip if date is missing
        if pd.isna(zen_date):
            continue
        
        # Process each amount column
        for amount_col in amount_columns:
            zen_amount = zen_row[amount_col]
            
            # Skip if amount is missing or zero
            if pd.isna(zen_amount) or zen_amount == 0:
                continue
            
            # Adjust sign for outcome (should be negative)
            if 'outcome' in amount_col.lower():
                zen_amount = -abs(zen_amount)
            
            # Find matching Credo transactions
            date_min = zen_date - pd.Timedelta(days=date_tolerance)
            date_max = zen_date + pd.Timedelta(days=date_tolerance)
            
            # Filter by date
            date_matches = credo_df[
                (credo_df['operationDateTime'] >= date_min) & 
                (credo_df['operationDateTime'] <= date_max)
            ]
            
            # Filter by amount with tolerance
            amount_min = zen_amount * (1 - amount_tolerance)
            amount_max = zen_amount * (1 + amount_tolerance)
            
            matches = date_matches[
                (date_matches['amount'] >= amount_min) & 
                (date_matches['amount'] <= amount_max)
            ]
            
            # Add to results
            for _, credo_row in matches.iterrows():
                # Check if this transaction is part of a currency transfer
                is_transfer = False
                transfer_info = {}
                
                if not transfers_df.empty:
                    # Check if transaction ID is in transfers_df
                    transfer_from = transfers_df[transfers_df['from_transaction_id'] == credo_row['transactionId']]
                    transfer_to = transfers_df[transfers_df['to_transaction_id'] == credo_row['transactionId']]
                    
                    if not transfer_from.empty:
                        is_transfer = True
                        transfer_row = transfer_from.iloc[0]
                        transfer_info = {
                            'transfer_type': 'from',
                            'transfer_pair_currency': transfer_row['to_currency'],
                            'transfer_pair_amount': transfer_row['to_amount'],
                            'transfer_pair_transaction_id': transfer_row['to_transaction_id'],
                            'exchange_rate': transfer_row['exchange_rate']
                        }
                    elif not transfer_to.empty:
                        is_transfer = True
                        transfer_row = transfer_to.iloc[0]
                        transfer_info = {
                            'transfer_type': 'to',
                            'transfer_pair_currency': transfer_row['from_currency'],
                            'transfer_pair_amount': transfer_row['from_amount'],
                            'transfer_pair_transaction_id': transfer_row['from_transaction_id'],
                            'exchange_rate': transfer_row['exchange_rate']
                        }
                
                row = {
                    'zen_date': zen_date,
                    'zen_amount': zen_amount,
                    'zen_amount_column': amount_col,
                    'credo_date': credo_row['operationDateTime'],
                    'credo_amount': credo_row['amount'],
                    'credo_description': credo_row['description'],
                    'credo_currency': credo_row['currency'],
                    'credo_transaction_id': credo_row['transactionId'],
                    'match_quality': 'exact' if abs(zen_amount - credo_row['amount']) < 0.01 else 'approximate',
                    'is_currency_transfer': is_transfer
                }
                
                # Add transfer info if this is part of a currency transfer
                if is_transfer:
                    row.update(transfer_info)
                
                # Add all zen columns
                for col in zen_df.columns:
                    row[f'zen_{col}'] = zen_row[col]
                
                result.append(row)
    
    if not result:
        if verbose:
            print("No matches found", file=sys.stderr)
        return pd.DataFrame()
    
    return pd.DataFrame(result)


def main():
    """Main function."""
    args = parse_args()
    
    # Load data
    zen_df = load_zen_csv(args.zen_csv, args.date_format, args.header_row)
    credo_df = load_credo_json(args.credo_json)
    
    if args.verbose:
        print(f"Loaded {len(zen_df)} ZenMoney transactions", file=sys.stderr)
        print(f"Loaded {len(credo_df)} Credo bank transactions", file=sys.stderr)
    
    # Find currency transfers
    transfers_df = find_currency_transfers(credo_df, verbose=args.verbose)
    
    # Save transfers to file if requested
    if args.transfers and not transfers_df.empty:
        transfers_df.to_csv(args.transfers, index=False)
        if args.verbose:
            print(f"Currency transfers saved to {args.transfers}", file=sys.stderr)
    
    # Match transactions
    result_df = match_transactions(
        zen_df, 
        credo_df,
        transfers_df,
        date_tolerance=args.tolerance, 
        amount_tolerance=args.amount_tolerance,
        verbose=args.verbose
    )
    
    if args.verbose:
        print(f"Found {len(result_df)} matches", file=sys.stderr)
    
    # Output
    if args.output:
        result_df.to_csv(args.output, index=False)
        if args.verbose:
            print(f"Results saved to {args.output}", file=sys.stderr)
    else:
        result_df.to_csv(sys.stdout, index=False)


if __name__ == "__main__":
    main()