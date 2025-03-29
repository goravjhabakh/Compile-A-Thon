#include<iostream>
using namespace std;

int main () {
    int m1[3][4] = {{1,2,3,4},{2,3,4,1},{3,4,1,2}};
    int m2[4][2] = {{1,2},{3,4},{1,4},{2,3}};
    int m3[3][2] = {{0,0},{0,0},{0,0}};

    //Multiply
    for (int i = 0; i < 3; i++) {      
        for (int j = 0; j < 2; j++) {   
            for (int k = 0; k < 4; k++) {
                m3[i][j] += m1[i][k] * m2[k][j];
            }
        }
    }

    // Print the matrix
    for (int i=0;i<3;i++) {
        for (int j=0;j<2;j++) {
            cout << m3[i][j] << " ";
        }
        cout << "\n";
    }
}