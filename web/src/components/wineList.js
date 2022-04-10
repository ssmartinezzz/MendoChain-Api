import React, { useState, useEffect } from 'react';
import Wine from './wine';
import { deleteWine, getAll } from '../services/wineService.js';
import { makeStyles } from '@material-ui/core/styles';
import Table from '@material-ui/core/Table';
import TableBody from '@material-ui/core/TableBody';
import TableCell from '@material-ui/core/TableCell';
import TableContainer from '@material-ui/core/TableContainer';
import TableHead from '@material-ui/core/TableHead';
import TableRow from '@material-ui/core/TableRow';
import Paper from '@material-ui/core/Paper';

const useStyles = makeStyles({
    table: {
        minWidth: 650,
    },
});

const WineList = () => {
   
    const classes = useStyles();
    const [wineList, setwineList] = useState([]);

    const getResources = () => {
            getAll()
            .then((data) => {
                setwineList(data);
            })
            .catch((error) => {
                console.log(error);
            });
    };

    useEffect(() => {
        getResources();
    }, []);

    const deleteResource = (event, id) => {
        event.preventDefault();
            deleteWine(id)
            .then((data) => {
                getResources();
            })
            .catch((error) => {
                console.log(error);
            });
    };

    return (
        <div className='container-table'>
            <TableContainer component={Paper}>
                <Table className={classes.table} aria-label='simple table'>
                    <TableHead>
                        <TableRow>
                            <TableCell align='left'>
                                <h2>Variety name</h2>
                            </TableCell>
                            <TableCell align='left'>
                                <h2>Content</h2>
                            </TableCell>
                            <TableCell align='left'>
                                <h2>Alcohol</h2>
                            </TableCell>
                            <TableCell align='left'>
                                <h2>Brand_name</h2>
                            </TableCell>
                            <TableCell align='left'>
                                <h2>Lote</h2>
                            </TableCell>

                            <TableCell align='left' className='table-cell-btn'></TableCell>
                        </TableRow>
                    </TableHead>
                    <TableBody>
                        {wineList.map((instance, index) => (
                            <Wine wine={instance} callBack={deleteResource} key={index} />
                        ))}
                    </TableBody>
                </Table>
            </TableContainer>
        </div>
    );
};

export default WineList;
