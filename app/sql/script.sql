create database prueba

use prueba

create table usuarios(
    id int auto_increment,
    nombre varchar(20) not null,
    apellido varchar(20) not null,
    cedula varchar(20) not null,
    edad int not null,
    usuario varchar(20)  not null,
    contrasena varchar(20)  not null,
    primary key(id)
)

insert into usuarios (nombre,apellido,cedula,edad,usuario,contrasena)
values ('pedro','perez','10102020',30,'pperez','12345')