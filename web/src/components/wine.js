import React from 'react';
import TableRow from '@material-ui/core/TableRow';
import TableCell from '@material-ui/core/TableCell';

const Wine = ({ wine, callBack }) => {
    return (
        <TableRow key={wine.id}>

            <TableCell align='left'>{wine.variety_name}</TableCell>
            <TableCell align='left'>{wine.content}</TableCell>
            <TableCell align='left'>{wine.alcohol}</TableCell>
            <TableCell align='left'>{wine.brand_name}</TableCell>
            <TableCell align='left'>{wine.lote}</TableCell>

            <TableCell
                align='center'
                className='table-cell-btn'
                onClick={(event) => callBack(event, wine.id)}>
                <i className='fas fa-trash-alt'></i>
            </TableCell>
        </TableRow>
    );
};

export default Wine;
