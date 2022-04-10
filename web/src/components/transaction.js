import React from 'react';
import TableRow from '@material-ui/core/TableRow';
import TableCell from '@material-ui/core/TableCell';

const Transaction = ({ transaction, callBack }) => {
    return (
        <TableRow key={transaction.id}>
            <TableCell align='left'>{transaction.quantity}</TableCell>
            <TableCell align='left'>{transaction.transaction_id}</TableCell>

            <TableCell align='left'>{transaction.wine}</TableCell>
            <TableCell
                align='center'
                className='table-cell-btn'
                onClick={(event) => callBack(event, transaction.id)}>
                <i className='fas fa-trash-alt'></i>
            </TableCell>
        </TableRow>
    );
};

export default Transaction;
