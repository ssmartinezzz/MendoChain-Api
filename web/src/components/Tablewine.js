import React from 'react'

export const Tablewine = ({handleChange, quantity}) => {
  return (
    <table className='table table-dark table-hover'>
    <thead>
        <tr>
            <th scope='col'>#</th>
            <th scope='col'>Wine</th>
            <th scope='col'>Quantity</th>
            <th scope='col'>Action</th>
        </tr>
    </thead>
    <tbody>
        <>
            <th scope='row'></th>
            
            <td className='text-white' ></td>
            <td>
                <input className='text-white'
                    min={0}
                    type='number'
                    name='quantity'
                    value={quantity}
                    onChange={handleChange}
                />
            </td>
            <td>
                <input className='bg-dark text-white' type='submit' value='Go' />
            </td>
        </>
    </tbody>
</table>
  )
}
